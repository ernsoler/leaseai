import os

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_budgets as budgets,
)
from constructs import Construct


class LeaseAIStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, env_name: str = "dev", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        def name(resource: str) -> str:
            """Return a lowercase resource name following project nomenclature."""
            return f"leaseai-{env_name}-{resource}"

        # ── S3 bucket for PDF storage ────────────────────────────────────────
        pdf_bucket = s3.Bucket(
            self,
            "PdfBucket",
            bucket_name=name("pdfs"),
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireUploads",
                    expiration=Duration.hours(24),
                    prefix="uploads/",
                )
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    # TODO: restrict to frontend domain once hosting is confirmed
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3000,
                )
            ],
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # ── DynamoDB: analyses table ─────────────────────────────────────────
        analyses_table = dynamodb.Table(
            self,
            "AnalysesTable",
            table_name=name("analyses"),
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(
                name="analysis_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            time_to_live_attribute="expire_at",
        )
        analyses_table.add_global_secondary_index(
            index_name="created_at-index",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(
                name="created_at", type=dynamodb.AttributeType.STRING),
        )

        # ── SQS: analyze-jobs queue + DLQ ────────────────────────────────────
        analyze_jobs_dlq = sqs.Queue(
            self,
            "AnalyzeJobsDlq",
            queue_name=name("analyze-jobs-dlq"),
            retention_period=Duration.days(14),
        )

        analyze_jobs_queue = sqs.Queue(
            self,
            "AnalyzeJobsQueue",
            queue_name=name("analyze-jobs"),
            # Visibility timeout must be >= Lambda timeout to prevent double-processing
            visibility_timeout=Duration.seconds(900),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=2,
                queue=analyze_jobs_dlq,
            ),
        )

        # ── Shared Lambda environment ────────────────────────────────────────
        common_env = {
            "BUCKET_NAME": pdf_bucket.bucket_name,
            "ANALYSES_TABLE": analyses_table.table_name,
            # AI_MODEL: set in .env to pin a specific model, leave blank for provider default.
            "AI_MODEL": os.environ.get("AI_MODEL", ""),
            "AI_PROVIDER": os.environ.get("AI_PROVIDER", "anthropic"),
        }

        # ── Lambda: presign ──────────────────────────────────────────────────
        presign_fn = lambda_.Function(
            self,
            "PresignFunction",
            function_name=name("presign"),
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="backend.handlers.presign.handler",
            code=lambda_.Code.from_asset("../backend/dist/presign.zip"),
            memory_size=256,
            timeout=Duration.seconds(30),
            environment=common_env,
        )
        pdf_bucket.grant_put(presign_fn)

        # ── Provider API key injection ────────────────────────────────────────
        # Inject whichever API key(s) are present in the deploy environment.
        # ai_client.py reads each provider's own env var, so we forward all
        # non-empty ones rather than hard-coding a single provider at deploy time.
        # Set the relevant key in .env before running `make deploy`:
        #   ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, or OLLAMA_BASE_URL
        _provider_key_vars = (
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GOOGLE_API_KEY",
            "OLLAMA_BASE_URL",
        )
        provider_keys = {
            var: os.environ[var]
            for var in _provider_key_vars
            if os.environ.get(var)
        }

        # ── Lambda: process (heavy SQS worker) ───────────────────────────────
        process_fn = lambda_.Function(
            self,
            "ProcessFunction",
            function_name=name("process"),
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="backend.handlers.process.handler",
            code=lambda_.Code.from_asset("../backend/dist/process.zip"),
            memory_size=512,
            timeout=Duration.seconds(900),
            environment={
                **common_env,
                **provider_keys,
            },
        )
        pdf_bucket.grant_read(process_fn)
        analyses_table.grant_read_write_data(process_fn)
        analyze_jobs_queue.grant_consume_messages(process_fn)

        # ── Concurrency cap on process Lambda ────────────────────────────────
        # Hard ceiling: protects Anthropic rate limits under load spikes.
        # At 5 concurrent × ~50s per analysis = ~6 jobs/min throughput.
        # Tune up if Anthropic tier allows higher TPM; tune down if you hit 529s.
        process_fn.add_event_source(
            lambda_event_sources.SqsEventSource(
                analyze_jobs_queue,
                batch_size=1,
                # max_concurrency caps simultaneous process Lambda invocations.
                # SQS buffers all overflow jobs — they are not lost, just queued.
                max_concurrency=5,
            )
        )
        # Reserved concurrency ensures process Lambda always gets Lambda capacity
        # even if other functions in the account spike. Set to match max_concurrency.
        process_fn.add_to_resource_policy = None  # no-op, just for documentation
        # NOTE: reserved_concurrent_executions intentionally not set here —
        # throttling at SqsEventSource.max_concurrency is the right lever.
        # Setting reserved_concurrent_executions additionally would cause SQS
        # throttle errors that inflate the receive count toward the DLQ.

        # ── Lambda: get-results ──────────────────────────────────────────────
        get_results_fn = lambda_.Function(
            self,
            "GetResultsFunction",
            function_name=name("get-results"),
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="backend.handlers.get_results.handler",
            code=lambda_.Code.from_asset("../backend/dist/get_results.zip"),
            memory_size=256,
            timeout=Duration.seconds(30),
            environment=common_env,
        )
        analyses_table.grant_read_data(get_results_fn)

        # ── API Gateway ──────────────────────────────────────────────────────
        api = apigw.RestApi(
            self,
            "LeaseAIApi",
            rest_api_name=name("api"),
            description="LeaseAI REST API",
            default_cors_preflight_options=apigw.CorsOptions(
                # TODO: restrict to frontend domain once hosting is confirmed
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Api-Key", "x-api-key"],
            ),
            deploy_options=apigw.StageOptions(stage_name=env_name),
        )

        # POST /upload-url
        upload_url_resource = api.root.add_resource("upload-url")
        upload_url_resource.add_method(
            "POST",
            apigw.LambdaIntegration(presign_fn),
        )

        # GET /analysis/{id}
        analysis_resource = api.root.add_resource("analysis")
        analysis_id_resource = analysis_resource.add_resource("{id}")
        analysis_id_resource.add_method(
            "GET",
            apigw.LambdaIntegration(get_results_fn),
        )

        # ── Lambda: submit ────────────────────────────────────────────────────
        submit_fn = lambda_.Function(
            self,
            "SubmitFunction",
            function_name=name("submit"),
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="backend.handlers.submit.handler",
            code=lambda_.Code.from_asset("../backend/dist/submit.zip"),
            memory_size=256,
            timeout=Duration.seconds(30),
            environment={
                **common_env,
                "ANALYSES_QUEUE_URL": analyze_jobs_queue.queue_url,
                "FRONTEND_URL": os.environ.get("FRONTEND_URL", "https://leaseai.vercel.app"),
                "USER_ID": os.environ.get("USER_ID", "demo"),
            },
        )
        analyses_table.grant_read_write_data(submit_fn)
        analyze_jobs_queue.grant_send_messages(submit_fn)

        # POST /submit
        submit_resource = api.root.add_resource("submit")
        submit_resource.add_method(
            "POST",
            apigw.LambdaIntegration(submit_fn),
        )

        # ── Observability: SNS topic for alarms ──────────────────────────────
        # Subscribe an email or PagerDuty endpoint manually in the AWS console
        # after first deploy (CDK cannot manage email subscriptions).
        alarm_topic = sns.Topic(
            self,
            "AlarmTopic",
            topic_name=name("alarms"),
            display_name=f"LeaseAI {env_name} Alarms",
        )

        # ── Alarm: DLQ has messages → a job failed all retries ───────────────
        # Any message in the DLQ means a job was permanently failed.
        cloudwatch.Alarm(
            self,
            "DlqMessagesAlarm",
            alarm_name=name("dlq-messages"),
            alarm_description="Jobs are landing in the DLQ — process Lambda is failing after all retries.",
            metric=analyze_jobs_dlq.metric_approximate_number_of_messages_visible(
                period=Duration.minutes(1),
                statistic="Sum",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # ── Alarm: queue depth growing → consumers can't keep up ─────────────
        # Under stress: jobs queue faster than process Lambda can drain them.
        # 50 = ~8 minutes of backlog at max_concurrency=5 + 50s/job.
        # Lower this threshold if you need tighter SLA guarantees.
        cloudwatch.Alarm(
            self,
            "QueueDepthAlarm",
            alarm_name=name("queue-depth-high"),
            alarm_description="SQS queue depth is high — system may be under heavy load or process Lambda is slow.",
            metric=analyze_jobs_queue.metric_approximate_number_of_messages_visible(
                period=Duration.minutes(5),
                statistic="Maximum",
            ),
            threshold=50,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # ── Alarm: process Lambda errors ─────────────────────────────────────
        cloudwatch.Alarm(
            self,
            "ProcessLambdaErrorsAlarm",
            alarm_name=name("process-lambda-errors"),
            alarm_description="process Lambda is throwing unhandled exceptions (retryable errors).",
            metric=process_fn.metric_errors(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=3,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # ── Alarm: process Lambda throttles ──────────────────────────────────
        # Throttles here mean Lambda account-level concurrency is exhausted
        # (not the SqsEventSource max_concurrency limit, which queues silently).
        cloudwatch.Alarm(
            self,
            "ProcessLambdaThrottlesAlarm",
            alarm_name=name("process-lambda-throttles"),
            alarm_description="process Lambda is being throttled at account level — raise account concurrency or reduce max_concurrency.",
            metric=process_fn.metric_throttles(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(cw_actions.SnsAction(alarm_topic))

        # ── Allow AWS Budgets to publish to the alarm SNS topic ──────────────
        alarm_topic.add_to_resource_policy(iam.PolicyStatement(
            principals=[iam.ServicePrincipal("budgets.amazonaws.com")],
            actions=["SNS:Publish"],
            resources=[alarm_topic.topic_arn],
        ))

        # ── AWS Budget: monthly cost alert ───────────────────────────────────
        budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=15, unit="USD"),
                budget_name=name("monthly-budget"),
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=80,  # alert at 80% = $12
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=alarm_topic.topic_arn,
                        )
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=100,  # alert at 100% = $15
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=alarm_topic.topic_arn,
                        )
                    ],
                ),
            ],
        )

        # ── Dashboard ────────────────────────────────────────────────────────
        dashboard = cloudwatch.Dashboard(
            self,
            "LeaseAIDashboard",
            dashboard_name=name("dashboard"),
        )
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="SQS Queue Depth",
                left=[
                    analyze_jobs_queue.metric_approximate_number_of_messages_visible(),
                    analyze_jobs_dlq.metric_approximate_number_of_messages_visible(),
                ],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="Process Lambda — Invocations / Errors / Duration",
                left=[
                    process_fn.metric_invocations(),
                    process_fn.metric_errors(),
                    process_fn.metric_throttles(),
                ],
                right=[process_fn.metric_duration()],
                width=12,
            ),
        )

        # ── Outputs ──────────────────────────────────────────────────────────
        CfnOutput(self, "ApiUrl", value=api.url,
                  description="API Gateway URL — set as VITE_API_URL")
        CfnOutput(self, "BucketName", value=pdf_bucket.bucket_name,
                  description="S3 Bucket")
        CfnOutput(self, "AnalyzeJobsQueueUrl", value=analyze_jobs_queue.queue_url,
                  description="SQS analyze-jobs URL")
        CfnOutput(self, "AlarmTopicArn", value=alarm_topic.topic_arn,
                  description="SNS topic for alarms — subscribe your email/PagerDuty here")
