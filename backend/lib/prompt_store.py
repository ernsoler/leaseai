"""
Prompt store — loads system and user prompt templates.

Resolution order for each prompt:
  1. Direct env var (SYSTEM_PROMPT / USER_PROMPT_TEMPLATE) — local dev / tests.
  2. Bundled file next to this module (backend/prompts/) — Lambda at runtime.
"""
import os
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@lru_cache(maxsize=None)
def _read_bundled(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    logger.info("Loading prompt from bundled file: %s", path)
    return path.read_text(encoding="utf-8")


def get_system_prompt() -> str:
    value = os.environ.get("SYSTEM_PROMPT", "")
    if value:
        return value
    return _read_bundled("system.txt")


def get_user_prompt_template() -> str:
    value = os.environ.get("USER_PROMPT_TEMPLATE", "")
    if value:
        return value
    return _read_bundled("user_template.txt")
