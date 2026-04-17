"""
Lease analysis prompt builder.

The actual system prompt and user prompt template are stored in S3
(or injected via env vars for local dev / tests) — not in this repo.

The user template must contain the token <<<LEASE_TEXT>>> which is
replaced at runtime with the extracted lease document text.
"""
from backend.lib.prompt_store import get_user_prompt_template

_LEASE_TEXT_TOKEN = "<<<LEASE_TEXT>>>"


def build_analysis_prompt(lease_text: str) -> str:
    """Build the user-turn prompt by injecting lease text into the S3 template."""
    template = get_user_prompt_template()
    if _LEASE_TEXT_TOKEN not in template:
        raise ValueError(
            f"User prompt template is missing the required token: {_LEASE_TEXT_TOKEN}"
        )
    return template.replace(_LEASE_TEXT_TOKEN, lease_text)
