"""
Model router for LeaseAI.

Resolves a (provider, model_id) pair from environment variables.
No user tiers — every request uses the same configured model.

Resolution order (first match wins):
  1. AI_MODEL env var  — uses this model string verbatim with the active provider
  2. AI_PROVIDER env var — uses this provider's default model
  3. Built-in default — Anthropic claude-haiku-4-5-20251001

Environment variables:
    AI_PROVIDER   Override the provider  (anthropic | openai | google | ollama)
    AI_MODEL      Override the model ID  (any provider-specific string)

Example:
    AI_PROVIDER=openai AI_MODEL=gpt-4o-mini
    → always uses OpenAI gpt-4o-mini

    AI_PROVIDER=openai  (no AI_MODEL)
    → uses OpenAI gpt-4o-mini (provider default)

    (neither set)
    → uses Anthropic claude-haiku-4-5-20251001
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass

from backend.lib.constants import AIProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelConfig:
    provider: str  # "anthropic" | "openai" | "google" | "ollama"
    model_id: str  # provider-specific model string


# Default model per provider when no AI_MODEL override is set.
PROVIDER_DEFAULTS: dict[str, ModelConfig] = {
    AIProvider.ANTHROPIC: ModelConfig(AIProvider.ANTHROPIC, "claude-haiku-4-5-20251001"),
    AIProvider.OPENAI:    ModelConfig(AIProvider.OPENAI,    "gpt-4o-mini"),
    AIProvider.GOOGLE:    ModelConfig(AIProvider.GOOGLE,    "gemini-1.5-flash"),
    AIProvider.OLLAMA:    ModelConfig(AIProvider.OLLAMA,    "llama3.1:8b"),
}

_DEFAULT_PROVIDER = AIProvider.ANTHROPIC


def get_model_config() -> ModelConfig:
    """
    Return a ModelConfig (provider, model_id) based on environment variables.

    Returns:
        ModelConfig with .provider and .model_id resolved.
    """
    env_provider = os.environ.get("AI_PROVIDER", "").strip().lower() or None
    env_model    = os.environ.get("AI_MODEL",    "").strip()         or None

    provider = env_provider or _DEFAULT_PROVIDER

    if env_model:
        config = ModelConfig(provider=provider, model_id=env_model)
        logger.info("model_router: env override provider=%s model=%s", provider, env_model)
        return config

    config = PROVIDER_DEFAULTS.get(provider)
    if config is None:
        valid = ", ".join(AIProvider)
        raise ValueError(
            f"AI_PROVIDER='{provider}' is not a recognised provider. "
            f"Valid options: {valid}"
        )

    logger.info("model_router: provider default provider=%s model=%s", config.provider, config.model_id)
    return config


def get_model() -> str:
    """Return just the model ID string. Convenience wrapper around get_model_config()."""
    return get_model_config().model_id
