VENV   := .venv
PIP    := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF   := $(VENV)/bin/ruff

.PHONY: install dev deploy test test-unit test-integration package clean

# ── Venv ─────────────────────────────────────────────────────────────────────
$(VENV):
	python3 -m venv $(VENV)

# ── Install ──────────────────────────────────────────────────────────────────
install: $(VENV)
	@echo "Installing backend dependencies..."
	$(PIP) install -e ".[dev]"
	@echo "Installing CDK dependencies..."
	cd infra && $(CURDIR)/$(PIP) install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && pnpm install

# ── Dev ───────────────────────────────────────────────────────────────────────
dev:
	cd frontend && pnpm dev

# ── Lint ──────────────────────────────────────────────────────────────────────
lint:
	$(RUFF) check backend/

lint-fix:
	$(RUFF) check backend/ --fix

# ── Test ──────────────────────────────────────────────────────────────────────
test:
	$(PYTEST) backend/tests/ -v --tb=short

test-unit:
	$(PYTEST) backend/tests/unit/ -v --tb=short

test-integration:
	$(PYTEST) backend/tests/integration/ -v --tb=short

# ── Package Lambdas ───────────────────────────────────────────────────────────
# Bundles each Lambda handler with its dependencies into a zip file.
# No Lambda Layers — dependencies are bundled directly per the spec.
package:
	@echo "Packaging Lambdas..."
	mkdir -p backend/dist

	@echo "Building presign.zip..."
	rm -rf /tmp/leaseai-presign && mkdir -p /tmp/leaseai-presign/backend
	pip install boto3 -t /tmp/leaseai-presign --quiet
	touch /tmp/leaseai-presign/backend/__init__.py
	cp -r backend/handlers /tmp/leaseai-presign/backend/
	cp -r backend/lib /tmp/leaseai-presign/backend/
	cp -r backend/prompts /tmp/leaseai-presign/backend/
	cd /tmp/leaseai-presign && zip -r9 $(PWD)/backend/dist/presign.zip . -x "*.pyc" -x "__pycache__/*"

	@echo "Building get_results.zip..."
	rm -rf /tmp/leaseai-results && mkdir -p /tmp/leaseai-results/backend
	pip install boto3 -t /tmp/leaseai-results --quiet
	touch /tmp/leaseai-results/backend/__init__.py
	cp -r backend/handlers /tmp/leaseai-results/backend/
	cp -r backend/lib /tmp/leaseai-results/backend/
	cp -r backend/prompts /tmp/leaseai-results/backend/
	cd /tmp/leaseai-results && zip -r9 $(PWD)/backend/dist/get_results.zip . -x "*.pyc" -x "__pycache__/*"

	@echo "Building submit.zip..."
	rm -rf /tmp/leaseai-submit && mkdir -p /tmp/leaseai-submit/backend
	pip install boto3 -t /tmp/leaseai-submit --quiet
	touch /tmp/leaseai-submit/backend/__init__.py
	cp -r backend/handlers /tmp/leaseai-submit/backend/
	cp -r backend/lib /tmp/leaseai-submit/backend/
	cp -r backend/prompts /tmp/leaseai-submit/backend/
	cd /tmp/leaseai-submit && zip -r9 $(PWD)/backend/dist/submit.zip . -x "*.pyc" -x "__pycache__/*"

	@echo "Building process.zip..."
	rm -rf /tmp/leaseai-process && mkdir -p /tmp/leaseai-process/backend
	pip install -r backend/requirements.txt -t /tmp/leaseai-process \
		--platform manylinux2014_x86_64 --implementation cp --python-version 312 \
		--only-binary=:all: --quiet
	touch /tmp/leaseai-process/backend/__init__.py
	cp -r backend/handlers /tmp/leaseai-process/backend/
	cp -r backend/lib /tmp/leaseai-process/backend/
	cp -r backend/prompts /tmp/leaseai-process/backend/
	cd /tmp/leaseai-process && zip -r9 $(PWD)/backend/dist/process.zip . -x "*.pyc" -x "__pycache__/*"

	@echo "Lambda packages ready in backend/dist/"

# ── Deploy ────────────────────────────────────────────────────────────────────
# Usage: make deploy ENV=dev  or  make deploy ENV=prd
#
# After deploy, the API Gateway URL is printed by CDK and also written to .env
# as VITE_API_URL automatically. Copy it into the frontend .env if needed.
ENV ?= dev
deploy: package
	$(eval export CDK_DEFAULT_ACCOUNT=$(shell aws sts get-caller-identity --query Account --output text))
	$(eval export CDK_DEFAULT_REGION?=us-east-1)
	@set -a; [ -f .env ] && . ./.env; set +a; cd infra && cdk deploy --context env=$(ENV) --require-approval never --outputs-file /tmp/leaseai-outputs.json
	@python3 -c " \
import json, re, os; \
d = list(json.load(open('/tmp/leaseai-outputs.json')).values())[0]; \
api_url = d.get('ApiUrl', '').rstrip('/'); \
fe_env_path = 'frontend/.env.local'; \
fe_env = open(fe_env_path).read() if os.path.exists(fe_env_path) else ''; \
pat = r'^VITE_API_URL=.*'; \
line = f'VITE_API_URL={api_url}'; \
fe_env = re.sub(pat, line, fe_env, flags=re.M) if re.search(pat, fe_env, re.M) else fe_env + line + '\\n'; \
open(fe_env_path,'w').write(fe_env); \
print(); print(f'API URL : {api_url}'); print(f'Written to {fe_env_path}'); \
" 2>/dev/null || echo "(Could not auto-write frontend/.env.local — check /tmp/leaseai-outputs.json)"

# ── Upload prompts to S3 ──────────────────────────────────────────────────────
# Run once after deploy (or whenever prompts change).
# Usage: make upload-prompts ENV=dev
upload-prompts:
	aws s3 cp backend/prompts/system.txt       s3://leaseai-$(ENV)-pdfs/prompts/system.txt
	aws s3 cp backend/prompts/user_template.txt s3://leaseai-$(ENV)-pdfs/prompts/user_template.txt
	@echo "Prompts uploaded to s3://leaseai-$(ENV)-pdfs/prompts/"

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	rm -rf backend/dist/
	rm -rf frontend/dist/
	rm -rf frontend/node_modules/
	rm -rf infra/cdk.out/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
