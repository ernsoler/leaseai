# LeaseAI

> Upload a PDF lease agreement — get a structured AI-generated risk report in under 90 seconds.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![AWS CDK](https://img.shields.io/badge/AWS_CDK-v2-FF9900?logo=amazonaws)](https://aws.amazon.com/cdk/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript)](https://typescriptlang.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Portfolio project — a fully deployable serverless SaaS demonstrating async job pipelines, multi-provider AI integration, and infrastructure as code on AWS.

---

## Demo

https://github.com/user-attachments/assets/3ffaa5db-11e8-46d5-96ea-fd5c331c57c0

---

## What it does

Tenants upload a PDF rental agreement and receive a plain-English risk report that:

- **Risk score** (0–100) with breakdown by category (financial, legal, maintenance, termination)
- **Clause analysis** — flags risky clauses with explanations and negotiation tips
- **Financial summary** — monthly cost, move-in total, hidden fees and penalties
- **Key dates** — auto-renewal deadlines, deposit return windows, notice requirements
- **Missing protections** — clauses that should be there but aren't

A fully interactive **static demo** runs in the browser with zero API credentials.

---

## Architecture

```
Browser
  │
  ├── POST /upload-url  →  presign Lambda  →  S3 presigned PUT URL
  │                                             │
  │   (browser uploads PDF directly to S3) ────┘
  │
  ├── POST /submit      →  submit Lambda   →  DynamoDB (pending)
  │                                        →  SQS (analyze-jobs)
  │                                             │
  │                              process Lambda ┘  (SQS trigger)
  │                                ├── S3: download PDF
  │                                ├── PDF parser (PyMuPDF)
  │                                ├── AI call (Claude / OpenAI / Gemini / Ollama)
  │                                ├── Pydantic validation
  │                                └── DynamoDB (completed)
  │
  └── GET  /analysis/{id}  →  get-results Lambda  →  DynamoDB read
```

**Async pipeline** — submit returns immediately with an `analysis_id`. The frontend polls every 3 seconds until `status=completed`. No webhooks, no websockets.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.12, AWS Lambda |
| IaC | AWS CDK v2 (Python) |
| Database | DynamoDB (PAY_PER_REQUEST, TTL-enabled) |
| Storage | S3 (presigned PUT, 24h upload TTL) |
| Queue | SQS + DLQ (max_concurrency=5, visibility 900s) |
| AI | Anthropic Claude / OpenAI / Google Gemini / Ollama |
| Observability | CloudWatch alarms, DLQ alarm, budget alert |
| CI | GitHub Actions — lint + tests on every PR |

---

## Project structure

```
leaseai/
├── backend/
│   ├── handlers/           Lambda entry points
│   │   ├── presign.py      POST /upload-url — S3 presigned PUT
│   │   ├── submit.py       POST /submit — write pending stub, enqueue SQS
│   │   ├── process.py      SQS worker — PDF → AI → DynamoDB
│   │   └── get_results.py  GET /analysis/{id} — poll for results
│   ├── lib/
│   │   ├── ai_client.py    Multi-provider AI client
│   │   ├── model_router.py Provider/model selection from env
│   │   ├── pdf_parser.py   PDF text extraction (PyMuPDF)
│   │   ├── prompt_store.py Loads prompts from bundled files or env
│   │   ├── schema.py       Pydantic models for AI response validation
│   │   └── constants.py    StrEnum constants (status values, providers)
│   ├── prompts/
│   │   ├── system.txt      System prompt for the AI
│   │   └── user_template.txt  User prompt template (<<<LEASE_TEXT>>> placeholder)
│   └── tests/
│       ├── unit/           Fast moto-backed unit tests per handler
│       └── integration/    Full pipeline: submit → process → get_results
├── infra/
│   ├── app.py              CDK app entry point
│   └── leaseai_stack.py    All AWS resources in one stack
├── frontend/               React + Vite SPA
│   └── src/
│       ├── App.tsx         State machine: upload → polling → results
│       ├── hooks/
│       │   ├── useUpload.ts   S3 presigned upload flow
│       │   └── useAnalysis.ts Polling hook (3s interval, 5min timeout)
│       ├── components/
│       │   ├── landing/    Hero, HowItWorks, FAQ
│       │   ├── demo/       Static demo (no API calls)
│       │   ├── upload/     UploadZone, PaymentFlow
│       │   └── results/    AnalysisResults, RiskScore, ClauseCard,
│       │                   FinancialBreakdown, KeyDatesTimeline, RedFlags
│       ├── data/demoAnalysis.ts  Static demo data
│       └── lib/api.ts      Thin fetch wrapper
└── scripts/
    └── generate_test_lease.py  Generates a realistic test PDF (reportlab)
```

---

## Quick start

### Prerequisites

- Python 3.12+
- Node 18+ with [pnpm](https://pnpm.io)
- AWS CLI configured (`aws configure` or SSO)
- AWS CDK v2 — `npm install -g aws-cdk`
- An AI provider API key (Anthropic, OpenAI, Google, or local Ollama)

### 1. Install dependencies

```bash
make install
```

This installs Python backend deps, CDK infra deps, and frontend pnpm deps in one step.

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```bash
ANTHROPIC_API_KEY=sk-ant-...   # or OPENAI_API_KEY / GOOGLE_API_KEY / OLLAMA_BASE_URL
USER_ID=demo                   # any string — identifies your deployment
```

### 3. Run the frontend locally

```bash
make dev
# → http://localhost:5173
```

The demo section works immediately — no API calls, no credentials needed.

### 4. Deploy to AWS

```bash
# Authenticate with AWS first
aws sso login --profile your-profile   # or: export AWS_ACCESS_KEY_ID=... etc.

make deploy ENV=dev
```

`make deploy` will:
1. Package all Lambda functions into zip files under `backend/dist/`
2. Run `cdk deploy` with your `.env` vars injected
3. Write the API Gateway URL to `frontend/.env.local` automatically

### 5. Run tests

```bash
make test              # all tests
make test-unit         # unit tests only (fast, no AWS)
make test-integration  # full pipeline via moto fakes
```

---

## Makefile reference

| Command | Description |
|---|---|
| `make install` | Install all dependencies (backend + CDK + frontend) |
| `make dev` | Start frontend dev server on `localhost:5173` |
| `make test` | Run all pytest tests |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make lint` | Lint backend with ruff |
| `make lint-fix` | Auto-fix lint issues |
| `make package` | Build Lambda zip files into `backend/dist/` |
| `make deploy ENV=dev` | Package + deploy to AWS (`ENV=dev` or `ENV=prd`) |
| `make clean` | Remove build artifacts and generated files |

---

## AI provider configuration

Switch providers by setting `AI_PROVIDER` in `.env` before deploying:

| `AI_PROVIDER` | API key env var | Notes |
|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | Default — Claude Haiku |
| `openai` | `OPENAI_API_KEY` | GPT-4o Mini |
| `google` | `GOOGLE_API_KEY` | Gemini 1.5 Flash |
| `ollama` | `OLLAMA_BASE_URL` | Fully local, no key needed |

Pin a specific model with `AI_MODEL=claude-sonnet-4-6` (optional).

---

## Key design decisions

- **No auth on public routes** — `presign`, `submit`, `get_results` are public. Ownership is enforced via the DynamoDB composite key `(user_id, analysis_id)`.
- **Fixed `USER_ID`** — this is a demo deployment with a single identity. Set `USER_ID` in `.env` to any string you like.
- **Prompts bundled in the Lambda zip** — no S3 upload step needed. Prompts live in `backend/prompts/` and are copied into every zip at package time.
- **Pydantic validation gate** — if the AI response fails schema validation, the item is marked `status=failed` rather than stored with bad data.
- **No Lambda Layers** — each Lambda is a self-contained zip with all dependencies bundled. Simpler to reason about, easier to deploy.
- **SQS concurrency cap** — `max_concurrency=5` on the SQS event source protects against AI rate limit spikes. Overflow jobs queue silently — nothing is lost.

---

## GitHub Actions

CI runs on every PR — no deploy automation, credentials never leave your machine.

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | Push / PR | `ruff` lint + `pytest` |
| `claude.yml` | PR | Claude AI code review |

Required secret: `ANTHROPIC_API_KEY`

---

## Generate a test lease PDF

```bash
pip install -e ".[dev]"
python3.12 scripts/generate_test_lease.py
# → lease_agreement_test.pdf
```

Generates a realistic Florida single-family home lease (modelled on the official FL BAR form) with intentionally risky clauses for testing the AI analysis pipeline.

---

## License

MIT — see [LICENSE](LICENSE).

> AI-generated analysis is for informational purposes only and does not constitute legal advice.
