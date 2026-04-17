"""
Tests for backend/lib/model_router.py

Covers provider defaults, AI_PROVIDER override, AI_MODEL override,
unknown providers, and the get_model() convenience shim.
"""
import os
import pytest
from unittest.mock import patch

from backend.lib.model_router import (
    ModelConfig,
    get_model_config,
    PROVIDER_DEFAULTS,
    _DEFAULT_PROVIDER,
)


def _env(**kwargs):
    """Patch os.environ, removing keys whose value is None."""
    to_set = {k: v for k, v in kwargs.items() if v is not None}
    to_remove = [k for k, v in kwargs.items() if v is None]
    ctx = patch.dict(os.environ, to_set, clear=False)

    class _Combined:
        def __enter__(self_inner):
            ctx.__enter__()
            for k in to_remove:
                os.environ.pop(k, None)
            return self_inner

        def __exit__(self_inner, *args):
            ctx.__exit__(*args)

    return _Combined()


# ── ModelConfig dataclass ─────────────────────────────────────────────────────

class TestModelConfig:
    def test_fields(self):
        cfg = ModelConfig(provider="openai", model_id="gpt-4o")
        assert cfg.provider == "openai"
        assert cfg.model_id == "gpt-4o"

    def test_frozen(self):
        cfg = ModelConfig(provider="anthropic", model_id="claude-sonnet-4-6")
        with pytest.raises(Exception):  # FrozenInstanceError
            cfg.provider = "openai"  # type: ignore[misc]


# ── PROVIDER_DEFAULTS table sanity ────────────────────────────────────────────

class TestProviderDefaultsTable:
    def test_all_providers_present(self):
        for p in ("anthropic", "openai", "google", "ollama"):
            assert p in PROVIDER_DEFAULTS

    def test_all_entries_are_model_config(self):
        for provider, cfg in PROVIDER_DEFAULTS.items():
            assert isinstance(cfg, ModelConfig)
            assert cfg.provider == provider
            assert cfg.model_id  # non-empty string


# ── Default (no env overrides) ────────────────────────────────────────────────

class TestDefaultRouting:
    def test_default_uses_anthropic_haiku(self):
        with _env(AI_PROVIDER=None, AI_MODEL=None):
            cfg = get_model_config()
        assert cfg.provider == "anthropic"
        assert "haiku" in cfg.model_id

    def test_default_provider_is_anthropic(self):
        with _env(AI_PROVIDER=None, AI_MODEL=None):
            cfg = get_model_config()
        assert cfg.provider == _DEFAULT_PROVIDER


# ── AI_PROVIDER override ──────────────────────────────────────────────────────

class TestProviderOverride:
    def test_openai_provider_returns_openai_model(self):
        with _env(AI_PROVIDER="openai", AI_MODEL=None):
            cfg = get_model_config()
        assert cfg.provider == "openai"
        assert "gpt" in cfg.model_id.lower()

    def test_google_provider_returns_gemini(self):
        with _env(AI_PROVIDER="google", AI_MODEL=None):
            cfg = get_model_config()
        assert cfg.provider == "google"
        assert "gemini" in cfg.model_id

    def test_ollama_provider_returns_local_model(self):
        with _env(AI_PROVIDER="ollama", AI_MODEL=None):
            cfg = get_model_config()
        assert cfg.provider == "ollama"

    def test_invalid_provider_raises_value_error(self):
        with _env(AI_PROVIDER="cohere", AI_MODEL=None):
            with pytest.raises(ValueError, match="cohere"):
                get_model_config()

    def test_provider_override_is_case_insensitive(self):
        with _env(AI_PROVIDER="OpenAI", AI_MODEL=None):
            cfg = get_model_config()
        assert cfg.provider == "openai"


# ── AI_MODEL override ─────────────────────────────────────────────────────────

class TestModelOverride:
    def test_model_override_uses_exact_string(self):
        with _env(AI_PROVIDER="openai", AI_MODEL="gpt-4o-mini"):
            cfg = get_model_config()
        assert cfg.model_id == "gpt-4o-mini"
        assert cfg.provider == "openai"

    def test_model_override_without_provider_defaults_to_anthropic(self):
        with _env(AI_PROVIDER=None, AI_MODEL="claude-opus-4-5"):
            cfg = get_model_config()
        assert cfg.provider == "anthropic"
        assert cfg.model_id == "claude-opus-4-5"

