# Self-Hosting LeaseAI

This document outlines the planned approach for running LeaseAI locally using Docker — no AWS account or paid services required.

## Planned Architecture

```
docker compose up
```

| Service | Technology |
|---|---|
| Frontend | React + Vite (this repo) |
| Backend API | FastAPI (Python 3.12) |
| Database | PostgreSQL or SQLite |
| File storage | Local filesystem or MinIO |
| Background jobs | Celery + Redis (or synchronous) |
| AI provider | Configurable — Anthropic, OpenAI, or Ollama (fully local) |

## Configuration

Developers will provide a `.env` file with their own credentials:

```env
# AI Provider — pick one
AI_PROVIDER=anthropic          # anthropic | openai | ollama
ANTHROPIC_API_KEY=sk-...       # required if AI_PROVIDER=anthropic
OPENAI_API_KEY=sk-...          # required if AI_PROVIDER=openai
OLLAMA_BASE_URL=http://ollama:11434  # required if AI_PROVIDER=ollama

# Prompts
SYSTEM_PROMPT_PATH=./prompts/system.txt
USER_PROMPT_TEMPLATE_PATH=./prompts/user_template.txt

# Storage
UPLOAD_DIR=./uploads           # local path for uploaded PDFs
DATABASE_URL=sqlite:///./leaseai.db

# App
SECRET_KEY=changeme
```

## Fully Local Option (no API keys needed)

Using [Ollama](https://ollama.ai) you can run the entire stack offline:

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
```

The `docker-compose.yml` will include an optional Ollama service for this use case.

## Status

> This self-hosted version is planned. The current codebase targets AWS (Lambda + DynamoDB + S3).
> Contributions welcome — see the architecture above for the target design.
