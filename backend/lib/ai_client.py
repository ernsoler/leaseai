"""
AI client abstraction layer for LeaseAI.

Provides a single AIClient interface that normalises responses from:
  - Anthropic  (Claude)
  - OpenAI     (GPT-4o, etc.)
  - Google     (Gemini)
  - Ollama     (local models via HTTP)

Provider selected via env var AI_PROVIDER (default: anthropic).
API keys read from env vars:
  ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY
Ollama needs no key — just OLLAMA_BASE_URL (default: http://localhost:11434).

Usage:
    from backend.lib.ai_client import get_ai_client
    client = get_ai_client(provider="anthropic", model="claude-sonnet-4-6")
    response = client.complete(system="...", user="...", max_tokens=4096)
    print(response.text, response.input_tokens, response.output_tokens)
"""
from __future__ import annotations

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# SSM secret resolver  (cached per Lambda container lifetime)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _ssm_get_parameter(param_name: str) -> str:
    import boto3  # noqa: PLC0415
    return boto3.client("ssm").get_parameter(
        Name=param_name, WithDecryption=True
    )["Parameter"]["Value"]


def _resolve_api_key(env_var: str, param_env_var: str) -> str:
    """Return the API key for a provider.

    Resolution order (first non-empty wins):
      1. Direct env var (e.g. ANTHROPIC_API_KEY) — used in local dev / tests.
      2. SSM SecureString whose path is stored in *_PARAM env var — used in Lambda.
    Result is cached for the container lifetime via lru_cache.
    """
    value = os.environ.get(env_var, "")
    if not value:
        param_name = os.environ.get(param_env_var, "")
        if param_name:
            value = _ssm_get_parameter(param_name)
    return value

# ---------------------------------------------------------------------------
# Cost table  (USD per 1 000 000 tokens — update as pricing changes)
# ---------------------------------------------------------------------------
MODEL_COSTS: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-haiku-4-5-20251001":  {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":          {"input": 3.00,  "output": 15.00},
    "claude-opus-4-5":            {"input": 15.00, "output": 75.00},
    # OpenAI
    "gpt-4o":                     {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":                {"input": 0.15,  "output": 0.60},
    "gpt-4-turbo":                {"input": 10.00, "output": 30.00},
    "o1":                         {"input": 15.00, "output": 60.00},
    # Google
    "gemini-1.5-pro":             {"input": 1.25,  "output": 5.00},
    "gemini-1.5-flash":           {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash":           {"input": 0.10,  "output": 0.40},
    # Ollama — local, treat as free
    "llama3":                     {"input": 0.00,  "output": 0.00},
    "mistral":                    {"input": 0.00,  "output": 0.00},
    "llama3.1:8b":                {"input": 0.00,  "output": 0.00},
    "llama3.3:70b":               {"input": 0.00,  "output": 0.00},
    "phi3":                       {"input": 0.00,  "output": 0.00},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated USD cost for a completion call."""
    costs = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens / 1_000_000 * costs["input"]) + \
           (output_tokens / 1_000_000 * costs["output"])


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------

@dataclass
class AIResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str

    @property
    def estimated_cost_usd(self) -> float:
        return estimate_cost(self.model, self.input_tokens, self.output_tokens)


# ---------------------------------------------------------------------------
# Provider error — wraps all SDK errors into a single provider-agnostic type
# ---------------------------------------------------------------------------

class ProviderError(Exception):
    """Raised by AIClient.complete() for any provider-side failure.

    Attributes:
        status_code: Suggested HTTP status code for the API response.
        retryable:   True if the caller should suggest the user retry.
        public_message: Safe message to return to the end user (no internal detail).
    """

    def __init__(self, public_message: str, status_code: int = 503, retryable: bool = False) -> None:
        super().__init__(public_message)
        self.status_code = status_code
        self.retryable = retryable
        self.public_message = public_message


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class AIClient(ABC):
    """All concrete clients implement this single interface."""

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 4096) -> AIResponse:
        """
        Send a completion request and return a normalised AIResponse.

        Args:
            system:     System / instruction prompt.
            user:       User-turn message.
            max_tokens: Maximum tokens in the response.

        Returns:
            AIResponse with text, token counts, model, and provider.
        """


# ---------------------------------------------------------------------------
# Anthropic  (Claude)
# ---------------------------------------------------------------------------

class AnthropicClient(AIClient):
    """Wraps the official anthropic SDK."""

    PROVIDER = "anthropic"

    def __init__(self, model: str, api_key: str) -> None:
        super().__init__(model)
        try:
            import anthropic as _anthropic  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "anthropic package is not installed. "
                "Run: pip install anthropic"
            ) from exc
        self._anthropic = _anthropic
        # 600s timeout — process Lambda has 900s; leaves ~300s headroom for internal
        # backoff retries (overloaded / rate-limit) before the Lambda itself times out.
        self._client = _anthropic.Anthropic(api_key=api_key, timeout=600.0)

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> AIResponse:
        # Use streaming so tokens are consumed as they arrive — prevents empty responses
        # on large leases where the non-streaming API can drop the connection on long outputs.
        try:
            with self._client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as stream:
                response = stream.get_final_message()
        except self._anthropic.AuthenticationError as e:
            logger.error("Anthropic auth error: %s", e)
            raise ProviderError("AI service configuration error.", status_code=503) from e
        except self._anthropic.PermissionDeniedError as e:
            logger.error("Anthropic permission error: %s", e)
            raise ProviderError("AI service configuration error.", status_code=503) from e
        except self._anthropic.RateLimitError as e:
            logger.warning("Anthropic rate limit: %s", e)
            raise ProviderError("AI service is busy. Please try again shortly.", status_code=429, retryable=True) from e
        except self._anthropic.APITimeoutError as e:
            logger.warning("Anthropic timeout: %s", e)
            raise ProviderError("Analysis timed out. Please try again.", status_code=503, retryable=True) from e
        except self._anthropic.BadRequestError as e:
            logger.error("Anthropic bad request: %s", e)
            raise ProviderError("AI service is temporarily unavailable.", status_code=503) from e
        except self._anthropic.APIStatusError as e:
            # overloaded_error can arrive in the stream body after an HTTP 200
            # (streaming starts, then the server sends an error event).
            error_type = ""
            if isinstance(getattr(e, "body", None), dict):
                error_type = e.body.get("error", {}).get("type", "")
            is_overloaded = error_type == "overloaded_error" or "overloaded" in str(e).lower()
            if is_overloaded:
                logger.warning("Anthropic overloaded (status=%s): %s", e.status_code, e)
                raise ProviderError(
                    "AI service is busy. Please try again shortly.",
                    status_code=503,
                    retryable=True,
                ) from e
            logger.error("Anthropic API error status=%s: %s", e.status_code, e)
            raise ProviderError("AI service is temporarily unavailable.", status_code=503, retryable=True) from e
        text = response.content[0].text if response.content else ""
        logger.info(
            "Anthropic response stop_reason=%s output_tokens=%d text_len=%d",
            response.stop_reason, response.usage.output_tokens, len(text),
        )
        if response.stop_reason == "max_tokens":
            logger.error(
                "Anthropic hit max_tokens limit model=%s output_tokens=%d — "
                "response is truncated and cannot be parsed",
                self.model, response.usage.output_tokens,
            )
            raise ProviderError(
                "The lease document is too large to analyse. "
                "Please try a shorter document or contact support.",
                status_code=422,
                retryable=False,
            )
        if not text.strip():
            raise ProviderError("Analysis service unavailable. Please try again.", status_code=503, retryable=True)
        return AIResponse(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
            provider=self.PROVIDER,
        )


# ---------------------------------------------------------------------------
# OpenAI  (GPT-4o, etc.)
# ---------------------------------------------------------------------------

class OpenAIClient(AIClient):
    """Wraps the official openai SDK (v1+)."""

    PROVIDER = "openai"

    def __init__(self, model: str, api_key: str) -> None:
        super().__init__(model)
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "openai package is not installed. "
                "Run: pip install openai"
            ) from exc
        self._client = OpenAI(api_key=api_key)

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> AIResponse:
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        choice = response.choices[0]
        usage = response.usage
        return AIResponse(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            model=self.model,
            provider=self.PROVIDER,
        )


# ---------------------------------------------------------------------------
# Google  (Gemini)
# ---------------------------------------------------------------------------

class GeminiClient(AIClient):
    """Wraps the google-generativeai SDK."""

    PROVIDER = "google"

    def __init__(self, model: str, api_key: str) -> None:
        super().__init__(model)
        try:
            import google.generativeai as genai  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "google-generativeai package is not installed. "
                "Run: pip install google-generativeai"
            ) from exc
        genai.configure(api_key=api_key)
        self._genai = genai

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> AIResponse:
        # google-generativeai passes system instruction at model config time
        model_instance = self._genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system,
            generation_config=self._genai.GenerationConfig(max_output_tokens=max_tokens),
        )
        response = model_instance.generate_content(user)

        # Attempt to read token counts from usage_metadata (available on most models)
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            input_tokens = getattr(meta, "prompt_token_count", 0) or 0
            output_tokens = getattr(meta, "candidates_token_count", 0) or 0

        return AIResponse(
            text=response.text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            provider=self.PROVIDER,
        )


# ---------------------------------------------------------------------------
# Ollama  (local HTTP API — bonus)
# ---------------------------------------------------------------------------

class OllamaClient(AIClient):
    """
    Calls a locally-running Ollama instance via its HTTP API.
    No API key required. Set OLLAMA_BASE_URL if Ollama is not on localhost.
    """

    PROVIDER = "ollama"

    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        super().__init__(model)
        try:
            import httpx  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "httpx package is not installed. "
                "Run: pip install httpx"
            ) from exc
        # 10-minute timeout — local models can be slow on first run
        self._http = httpx.Client(timeout=600.0)
        self._base_url = base_url.rstrip("/")

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> AIResponse:
        """
        Uses the /api/chat endpoint (Ollama >= 0.1.14).
        Falls back to /api/generate if /api/chat is unavailable.
        """
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {"role": "system",  "content": system},
                {"role": "user",    "content": user},
            ],
        }
        resp = self._http.post(f"{self._base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        text = data.get("message", {}).get("content", "")
        # Ollama reports prompt_eval_count / eval_count for token usage
        input_tokens = data.get("prompt_eval_count", 0) or 0
        output_tokens = data.get("eval_count", 0) or 0

        return AIResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            provider=self.PROVIDER,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_ai_client(provider: str, model: str) -> AIClient:
    """
    Instantiate the correct AIClient for the given provider.

    API keys / connection details are read from env vars:
        ANTHROPIC_API_KEY   — required for provider=anthropic
        OPENAI_API_KEY      — required for provider=openai
        GOOGLE_API_KEY      — required for provider=google
        OLLAMA_BASE_URL     — optional for provider=ollama (default localhost)

    Args:
        provider: One of "anthropic", "openai", "google", "ollama".
        model:    Provider-specific model identifier string.

    Returns:
        Concrete AIClient instance.

    Raises:
        ValueError:    Unknown provider string.
        ImportError:   Provider SDK not installed.
        RuntimeError:  Required API key env var is missing.
    """
    provider = provider.lower().strip()

    if provider == "anthropic":
        api_key = _resolve_api_key("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY_PARAM")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY env var (or ANTHROPIC_API_KEY_PARAM) is not set")
        return AnthropicClient(model=model, api_key=api_key)

    if provider == "openai":
        api_key = _resolve_api_key("OPENAI_API_KEY", "OPENAI_API_KEY_PARAM")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY env var (or OPENAI_API_KEY_PARAM) is not set")
        return OpenAIClient(model=model, api_key=api_key)

    if provider == "google":
        api_key = _resolve_api_key("GOOGLE_API_KEY", "GOOGLE_API_KEY_PARAM")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY env var (or GOOGLE_API_KEY_PARAM) is not set")
        return GeminiClient(model=model, api_key=api_key)

    if provider == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaClient(model=model, base_url=base_url)

    raise ValueError(
        f"Unknown AI provider: '{provider}'. "
        "Valid options: anthropic, openai, google, ollama"
    )
