#!/usr/bin/env python3
import os
import aws_cdk as cdk
from leaseai_stack import LeaseAIStack

app = cdk.App()

env_name = app.node.try_get_context("env") or "dev"

LeaseAIStack(
    app,
    f"LeaseAIStack-{env_name}",
    env_name=env_name,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    ),
)

app.synth()
