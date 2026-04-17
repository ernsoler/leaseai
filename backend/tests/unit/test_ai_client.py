"""
Tests for backend/lib/ai_client.py

All provider SDK calls are mocked — no real API keys needed.
"""
import os
import pytest
from unittest.mock import MagicMock, patch

from backend.lib.ai_client import (
    AIResponse,
    AnthropicClient,
    OpenAIClient,
    GeminiClient,
    OllamaClient,
    get_ai_client,
    estimate_cost,
    MODEL_COSTS,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _env(**kwargs):
    """Return an os.environ patch context with the given keys set."""
    return patch.dict(os.environ, kwargs, clear=False)


# ── AIResponse ────────────────────────────────────────────────────────────────

class TestAIResponse:
    def test_fields(self):
        r = AIResponse(text="hi", input_tokens=100, output_tokens=50,
                       model="claude-sonnet-4-6", provider="anthropic")
        assert r.text == "hi"
        assert r.input_tokens == 100
        assert r.output_tokens == 50
        assert r.model == "claude-sonnet-4-6"
        assert r.provider == "anthropic"

    def test_estimated_cost_known_model(self):
        r = AIResponse(text="", input_tokens=1_000_000, output_tokens=1_000_000,
                       model="claude-sonnet-4-6", provider="anthropic")
        # 3.00 input + 15.00 output = 18.00
        assert r.estimated_cost_usd == pytest.approx(18.00)

    def test_estimated_cost_unknown_model_is_zero(self):
        r = AIResponse(text="", input_tokens=500_000, output_tokens=500_000,
                       model="unknown-model-xyz", provider="anthropic")
        assert r.estimated_cost_usd == 0.0

    def test_estimated_cost_ollama_is_zero(self):
        r = AIResponse(text="", input_tokens=100_000, output_tokens=100_000,
                       model="llama3.1:8b", provider="ollama")
        assert r.estimated_cost_usd == 0.0


# ── estimate_cost ─────────────────────────────────────────────────────────────

class TestEstimateCost:
    def test_known_model(self):
        cost = estimate_cost("gpt-4o-mini", input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == pytest.approx(0.75)   # 0.15 + 0.60

    def test_unknown_model_returns_zero(self):
        assert estimate_cost("some-future-model", 999999, 999999) == 0.0

    def test_zero_tokens(self):
        assert estimate_cost("claude-sonnet-4-6", 0, 0) == 0.0

    def test_all_models_in_table_have_both_keys(self):
        for model, costs in MODEL_COSTS.items():
            assert "input" in costs, f"{model} missing 'input'"
            assert "output" in costs, f"{model} missing 'output'"


# ── AnthropicClient ───────────────────────────────────────────────────────────

class TestAnthropicClient:
    def _make_mock_sdk(self, text="result text", input_tokens=100, output_tokens=50):
        mock_sdk = MagicMock()
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        msg.stop_reason = "end_turn"
        msg.usage.input_tokens = input_tokens
        msg.usage.output_tokens = output_tokens
        # Wire the streaming context manager: client.messages.stream(...) is used
        stream_ctx = MagicMock()
        stream_ctx.__enter__ = MagicMock(return_value=stream_ctx)
        stream_ctx.__exit__ = MagicMock(return_value=False)
        stream_ctx.get_final_message.return_value = msg
        mock_sdk.Anthropic.return_value.messages.stream.return_value = stream_ctx
        return mock_sdk

    def test_complete_returns_airesponse(self):
        mock_sdk = self._make_mock_sdk("Hello!")
        with patch.dict("sys.modules", {"anthropic": mock_sdk}):
            client = AnthropicClient(model="claude-sonnet-4-6", api_key="test-key")
            resp = client.complete(system="sys", user="user msg")

        assert isinstance(resp, AIResponse)
        assert resp.text == "Hello!"
        assert resp.input_tokens == 100
        assert resp.output_tokens == 50
        assert resp.provider == "anthropic"
        assert resp.model == "claude-sonnet-4-6"

    def test_correct_args_forwarded_to_sdk(self):
        mock_sdk = self._make_mock_sdk()
        with patch.dict("sys.modules", {"anthropic": mock_sdk}):
            client = AnthropicClient(model="claude-haiku-4-5-20251001", api_key="key")
            client.complete(system="SYS", user="USER", max_tokens=2048)

        call_kwargs = mock_sdk.Anthropic.return_value.messages.stream.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["system"] == "SYS"
        assert call_kwargs["messages"] == [{"role": "user", "content": "USER"}]

    def test_overloaded_error_raises_retryable_provider_error(self):
        """overloaded_error in stream body (HTTP 200) must surface as retryable ProviderError."""
        from backend.lib.ai_client import ProviderError

        # Build a real exception hierarchy so `except self._anthropic.APIStatusError` works
        class _Never(Exception):
            pass
        class _FakeAPIStatusError(Exception):
            def __init__(self, body=None):
                super().__init__("Overloaded")
                self.status_code = 200
                self.body = body or {}

        mock_sdk = self._make_mock_sdk()  # wires stream context manager normally
        # Make get_final_message raise the overloaded error instead
        overloaded_body = {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}
        stream_ctx = mock_sdk.Anthropic.return_value.messages.stream.return_value
        stream_ctx.get_final_message.side_effect = _FakeAPIStatusError(body=overloaded_body)

        mock_sdk.APIStatusError = _FakeAPIStatusError
        for attr in ("AuthenticationError", "PermissionDeniedError", "RateLimitError",
                     "APITimeoutError", "BadRequestError"):
            setattr(mock_sdk, attr, _Never)

        with patch.dict("sys.modules", {"anthropic": mock_sdk}):
            client = AnthropicClient(model="claude-sonnet-4-6", api_key="key")
            with pytest.raises(ProviderError) as exc_info:
                client.complete(system="s", user="u")

        assert exc_info.value.retryable is True
        assert "busy" in exc_info.value.public_message.lower()

    def test_missing_sdk_raises_import_error(self):
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError, match="anthropic"):
                AnthropicClient(model="claude-sonnet-4-6", api_key="key")


# ── OpenAIClient ──────────────────────────────────────────────────────────────

class TestOpenAIClient:
    def _make_mock_sdk(self, text="gpt reply", prompt_tokens=80, completion_tokens=40):
        mock_sdk = MagicMock()
        choice = MagicMock()
        choice.message.content = text
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage.prompt_tokens = prompt_tokens
        resp.usage.completion_tokens = completion_tokens
        mock_sdk.OpenAI.return_value.chat.completions.create.return_value = resp
        return mock_sdk

    def test_complete_returns_airesponse(self):
        mock_sdk = self._make_mock_sdk("GPT answer")
        with patch.dict("sys.modules", {"openai": mock_sdk}):
            client = OpenAIClient(model="gpt-4o", api_key="sk-test")
            resp = client.complete(system="sys", user="user")

        assert isinstance(resp, AIResponse)
        assert resp.text == "GPT answer"
        assert resp.input_tokens == 80
        assert resp.output_tokens == 40
        assert resp.provider == "openai"
        assert resp.model == "gpt-4o"

    def test_system_message_placed_correctly(self):
        mock_sdk = self._make_mock_sdk()
        with patch.dict("sys.modules", {"openai": mock_sdk}):
            client = OpenAIClient(model="gpt-4o-mini", api_key="key")
            client.complete(system="SYSTEM PROMPT", user="USER MSG")

        messages = mock_sdk.OpenAI.return_value.chat.completions.create.call_args[1]["messages"]
        assert messages[0] == {"role": "system", "content": "SYSTEM PROMPT"}
        assert messages[1] == {"role": "user",   "content": "USER MSG"}

    def test_missing_sdk_raises_import_error(self):
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai"):
                OpenAIClient(model="gpt-4o", api_key="key")


# ── GeminiClient ──────────────────────────────────────────────────────────────

class TestGeminiClient:
    def _make_mock_genai(self, text="gemini reply", prompt_tokens=60, candidate_tokens=30):
        mock_genai = MagicMock()
        resp = MagicMock()
        resp.text = text
        resp.usage_metadata.prompt_token_count = prompt_tokens
        resp.usage_metadata.candidates_token_count = candidate_tokens
        mock_genai.GenerativeModel.return_value.generate_content.return_value = resp
        return mock_genai

    def test_complete_returns_airesponse(self):
        mock_genai = self._make_mock_genai("Gemini response")
        google_pkg = MagicMock()
        google_pkg.generativeai = mock_genai
        with patch.dict("sys.modules", {
            "google": google_pkg,
            "google.generativeai": mock_genai,
        }):
            client = GeminiClient(model="gemini-1.5-flash", api_key="AIza-test")
            resp = client.complete(system="sys", user="user")

        assert isinstance(resp, AIResponse)
        assert resp.text == "Gemini response"
        assert resp.input_tokens == 60
        assert resp.output_tokens == 30
        assert resp.provider == "google"
        assert resp.model == "gemini-1.5-flash"

    def test_system_instruction_passed_to_model_constructor(self):
        mock_genai = self._make_mock_genai()
        google_pkg = MagicMock()
        google_pkg.generativeai = mock_genai
        with patch.dict("sys.modules", {
            "google": google_pkg,
            "google.generativeai": mock_genai,
        }):
            client = GeminiClient(model="gemini-1.5-pro", api_key="key")
            client.complete(system="MY SYSTEM PROMPT", user="msg")

        call_kwargs = mock_genai.GenerativeModel.call_args[1]
        assert call_kwargs["system_instruction"] == "MY SYSTEM PROMPT"

    def test_missing_usage_metadata_defaults_to_zero(self):
        mock_genai = self._make_mock_genai()
        resp = mock_genai.GenerativeModel.return_value.generate_content.return_value
        resp.usage_metadata = None  # simulate missing metadata

        google_pkg = MagicMock()
        google_pkg.generativeai = mock_genai
        with patch.dict("sys.modules", {
            "google": google_pkg,
            "google.generativeai": mock_genai,
        }):
            client = GeminiClient(model="gemini-1.5-flash", api_key="key")
            resp_obj = client.complete(system="s", user="u")

        assert resp_obj.input_tokens == 0
        assert resp_obj.output_tokens == 0

    def test_missing_sdk_raises_import_error(self):
        with patch.dict("sys.modules", {"google": None, "google.generativeai": None}):
            with pytest.raises(ImportError, match="google-generativeai"):
                GeminiClient(model="gemini-1.5-flash", api_key="key")


# ── OllamaClient ──────────────────────────────────────────────────────────────

class TestOllamaClient:
    def _make_mock_httpx(self, text="ollama reply", prompt_eval=20, eval_count=15):
        # OllamaClient stores httpx.Client() as self._http and calls
        # self._http.post() directly — NOT as a context manager.
        mock_httpx = MagicMock()
        response = MagicMock()
        response.json.return_value = {
            "message": {"content": text},
            "prompt_eval_count": prompt_eval,
            "eval_count": eval_count,
        }
        mock_httpx.Client.return_value.post.return_value = response
        return mock_httpx

    def test_complete_returns_airesponse(self):
        mock_httpx = self._make_mock_httpx("Llama says hi")
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            client = OllamaClient(model="llama3.1:8b")
            resp = client.complete(system="sys", user="user")

        assert isinstance(resp, AIResponse)
        assert resp.text == "Llama says hi"
        assert resp.input_tokens == 20
        assert resp.output_tokens == 15
        assert resp.provider == "ollama"
        assert resp.model == "llama3.1:8b"

    def test_posts_to_correct_url(self):
        mock_httpx = self._make_mock_httpx()
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            client = OllamaClient(model="llama3.1:8b", base_url="http://myhost:11434")
            client.complete(system="s", user="u")

        post_call = mock_httpx.Client.return_value.post
        url = post_call.call_args[0][0]
        assert url == "http://myhost:11434/api/chat"

    def test_uses_default_base_url(self):
        mock_httpx = self._make_mock_httpx()
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            client = OllamaClient(model="llama3.1:8b")
        assert client._base_url == "http://localhost:11434"

    def test_trailing_slash_stripped_from_base_url(self):
        mock_httpx = self._make_mock_httpx()
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            client = OllamaClient(model="mistral:7b", base_url="http://localhost:11434/")
        assert not client._base_url.endswith("/")

    def test_missing_token_counts_default_to_zero(self):
        mock_httpx = MagicMock()
        response = MagicMock()
        response.json.return_value = {"message": {"content": "hi"}}  # no token fields
        mock_httpx.Client.return_value.post.return_value = response

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            client = OllamaClient(model="llama3.1:8b")
            resp = client.complete(system="s", user="u")

        assert resp.input_tokens == 0
        assert resp.output_tokens == 0

    def test_missing_sdk_raises_import_error(self):
        with patch.dict("sys.modules", {"httpx": None}):
            with pytest.raises(ImportError, match="httpx"):
                OllamaClient(model="llama3.1:8b")


# ── get_ai_client factory ─────────────────────────────────────────────────────

class TestGetAiClientFactory:
    def test_returns_anthropic_client(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_sdk}), \
             _env(ANTHROPIC_API_KEY="sk-test"):
            client = get_ai_client("anthropic", "claude-sonnet-4-6")
        assert isinstance(client, AnthropicClient)
        assert client.model == "claude-sonnet-4-6"

    def test_returns_openai_client(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_sdk}), \
             _env(OPENAI_API_KEY="sk-test"):
            client = get_ai_client("openai", "gpt-4o")
        assert isinstance(client, OpenAIClient)

    def test_returns_google_client(self):
        mock_genai = MagicMock()
        google_pkg = MagicMock()
        google_pkg.generativeai = mock_genai
        with patch.dict("sys.modules", {"google": google_pkg, "google.generativeai": mock_genai}), \
             _env(GOOGLE_API_KEY="AIza-test"):
            client = get_ai_client("google", "gemini-1.5-flash")
        assert isinstance(client, GeminiClient)

    def test_returns_ollama_client(self):
        mock_httpx = MagicMock()
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            client = get_ai_client("ollama", "llama3.1:8b")
        assert isinstance(client, OllamaClient)

    def test_provider_name_is_case_insensitive(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_sdk}), \
             _env(ANTHROPIC_API_KEY="key"):
            client = get_ai_client("ANTHROPIC", "claude-sonnet-4-6")
        assert isinstance(client, AnthropicClient)

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown"):
            get_ai_client("cohere", "command-r")

    def test_missing_anthropic_key_raises_runtime_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                get_ai_client("anthropic", "claude-sonnet-4-6")

    def test_missing_openai_key_raises_runtime_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                get_ai_client("openai", "gpt-4o")

    def test_missing_google_key_raises_runtime_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
                get_ai_client("google", "gemini-1.5-flash")

    def test_ollama_uses_env_base_url(self):
        mock_httpx = MagicMock()
        with patch.dict("sys.modules", {"httpx": mock_httpx}), \
             _env(OLLAMA_BASE_URL="http://gpu-box:11434"):
            client = get_ai_client("ollama", "llama3.3:70b")
        assert isinstance(client, OllamaClient)
        assert client._base_url == "http://gpu-box:11434"
