#!/usr/bin/env python3
"""
Multi-LLM Provider Architecture for AI Knowledge Filler.

Supports:
- Groq (Llama 3.3 - fast inference)
- Grok (xAI)
- Claude (Anthropic)
- Gemini (Google)
- GPT-3.5 (OpenAI)
- Ollama (local models)
"""

import importlib.util
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Type, List, Tuple

from exceptions import (
    LLMError,
    ProviderUnavailableError,
    ProviderTimeoutError,
    InvalidResponseError,
)
from logger import get_logger

logger = get_logger(__name__)

# ─── RETRY CONFIGURATION ──────────────────────────────────────────────────────

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0  # seconds; doubles each attempt: 1s, 2s, 4s

# Error substrings that indicate a retryable condition
_RETRYABLE_SIGNALS = (
    "timeout",
    "timed out",
    "rate limit",
    "429",
    "503",
    "502",
    "connection",
    "network",
    "temporarily unavailable",
    "overloaded",
)

# Error substrings that mean retrying is pointless
_FATAL_SIGNALS = (
    "401",
    "403",
    "invalid api key",
    "authentication",
    "permission denied",
    "not found",
    "404",
)

# Provider priority for fallback chain (fast/free-tier first)
FALLBACK_ORDER = ["groq", "grok", "claude", "gemini", "gpt4", "ollama"]


def _is_retryable(error: Exception) -> bool:
    """Determine whether an exception warrants a retry attempt.

    Args:
        error: The exception raised by the provider.

    Returns:
        True if the error is transient and retrying may succeed.
    """
    msg = str(error).lower()
    if any(sig in msg for sig in _FATAL_SIGNALS):
        return False
    if any(sig in msg for sig in _RETRYABLE_SIGNALS):
        return True
    # Default: retry unknown errors (conservative — network blips etc.)
    return True


# ─── BASE PROVIDER ────────────────────────────────────────────────────────────


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> str:
        """Generate content from user prompt with system instructions.

        Args:
            prompt: User's generation request.
            system_prompt: System instructions for the LLM.

        Returns:
            Generated markdown content.

        Raises:
            LLMError: If generation fails.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and ready to use.

        Returns:
            True if API key is set and library is installed.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'claude', 'gemini')."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name (e.g., 'Claude (Anthropic)')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier used by the provider."""


# ─── CLAUDE PROVIDER ──────────────────────────────────────────────────────────


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    def generate(self, prompt: str, system_prompt: str) -> str:
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderUnavailableError(
                self.name,
                reason="anthropic library not installed. Run: pip install anthropic",
            ) from exc

        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            content: str = str(response.content[0].text)
            if not content:
                raise InvalidResponseError(self.name, reason="empty response body")
            return content
        except (ProviderUnavailableError, InvalidResponseError):
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "timeout" in msg or "timed out" in msg:
                raise ProviderTimeoutError(self.name, timeout=120) from exc
            raise LLMError(
                f"Claude generation failed: {exc}",
                context={"provider": self.name, "model": self.model_name},
            ) from exc

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        return importlib.util.find_spec("anthropic") is not None

    @property
    def name(self) -> str:
        return "claude"

    @property
    def display_name(self) -> str:
        return "Claude (Anthropic)"

    @property
    def model_name(self) -> str:
        return "claude-sonnet-4-20250514"


# ─── GEMINI PROVIDER ──────────────────────────────────────────────────────────


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key. If None, uses GOOGLE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

    def generate(self, prompt: str, system_prompt: str) -> str:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ProviderUnavailableError(
                self.name,
                reason="google-genai library not installed. Run: pip install google-genai",
            ) from exc

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0),
            )
            content: str = str(response.text)
            if not content:
                raise InvalidResponseError(self.name, reason="empty response body")
            return content
        except (ProviderUnavailableError, InvalidResponseError):
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "timeout" in msg or "timed out" in msg:
                raise ProviderTimeoutError(self.name, timeout=120) from exc
            raise LLMError(
                f"Gemini generation failed: {exc}",
                context={"provider": self.name, "model": self.model_name},
            ) from exc

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        return importlib.util.find_spec("google.genai") is not None

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Gemini (Google)"

    @property
    def model_name(self) -> str:
        return "gemini-3-flash-preview"


# ─── OPENAI PROVIDER ──────────────────────────────────────────────────────────


class OpenAIProvider(LLMProvider):
    """OpenAI GPT-3.5 provider."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str, system_prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderUnavailableError(
                self.name,
                reason="openai library not installed. Run: pip install openai",
            ) from exc

        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0,
            )
            content: str = str(response.choices[0].message.content)
            if not content:
                raise InvalidResponseError(self.name, reason="empty response body")
            return content
        except (ProviderUnavailableError, InvalidResponseError):
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "timeout" in msg or "timed out" in msg:
                raise ProviderTimeoutError(self.name, timeout=120) from exc
            raise LLMError(
                f"OpenAI generation failed: {exc}",
                context={"provider": self.name, "model": self.model_name},
            ) from exc

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        return importlib.util.find_spec("openai") is not None

    @property
    def name(self) -> str:
        return "gpt4"

    @property
    def display_name(self) -> str:
        return "GPT-3.5 (OpenAI)"

    @property
    def model_name(self) -> str:
        return "gpt-3.5-turbo"


# ─── OLLAMA PROVIDER ──────────────────────────────────────────────────────────


class OllamaProvider(LLMProvider):
    """Ollama local models provider."""

    def __init__(self, model: Optional[str] = None):
        """Initialize Ollama provider.

        Args:
            model: Ollama model name. If None, uses OLLAMA_MODEL env var or default.
        """
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    def generate(self, prompt: str, system_prompt: str) -> str:
        try:
            import requests
        except ImportError as exc:
            raise ProviderUnavailableError(
                self.name,
                reason="requests library not installed. Run: pip install requests",
            ) from exc

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{prompt}",
            "stream": False,
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            content: str = str(response.json().get("response", ""))
            if not content:
                raise InvalidResponseError(self.name, reason="empty response body")
            return content
        except InvalidResponseError:
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "timeout" in msg or "timed out" in msg:
                raise ProviderTimeoutError(self.name, timeout=120) from exc
            raise LLMError(
                f"Ollama API error: {exc}",
                context={"provider": self.name, "url": url},
            ) from exc

    def is_available(self) -> bool:
        try:
            import requests

            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return bool(response.status_code == 200)
        except Exception:
            return False

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def display_name(self) -> str:
        return f"Ollama ({self.model})"

    @property
    def model_name(self) -> str:
        return self.model or "llama3.2:3b"


# ─── GROQ PROVIDER ────────────────────────────────────────────────────────────


class GroqProvider(LLMProvider):
    """Groq fast inference provider."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Groq provider.

        Args:
            api_key: Groq API key. If None, uses GROQ_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")

    def generate(self, prompt: str, system_prompt: str) -> str:
        try:
            from groq import Groq
        except ImportError as exc:
            raise ProviderUnavailableError(
                self.name,
                reason="groq library not installed. Run: pip install groq",
            ) from exc

        try:
            client = Groq(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0,
            )
            content: str = str(response.choices[0].message.content)
            if not content:
                raise InvalidResponseError(self.name, reason="empty response body")
            return content
        except (ProviderUnavailableError, InvalidResponseError):
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "timeout" in msg or "timed out" in msg:
                raise ProviderTimeoutError(self.name, timeout=120) from exc
            raise LLMError(
                f"Groq generation failed: {exc}",
                context={"provider": self.name, "model": self.model_name},
            ) from exc

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        return importlib.util.find_spec("groq") is not None

    @property
    def name(self) -> str:
        return "groq"

    @property
    def display_name(self) -> str:
        return "Groq (Llama 3.3)"

    @property
    def model_name(self) -> str:
        return "llama-3.3-70b-versatile"


# ─── XAI PROVIDER ─────────────────────────────────────────────────────────────


class XAIProvider(LLMProvider):
    """xAI Grok provider."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize xAI provider.

        Args:
            api_key: xAI API key. If None, uses XAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("XAI_API_KEY")

    def generate(self, prompt: str, system_prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderUnavailableError(
                self.name,
                reason="openai library not installed. Run: pip install openai",
            ) from exc

        try:
            client = OpenAI(api_key=self.api_key, base_url="https://api.x.ai/v1")
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0,
            )
            content: str = str(response.choices[0].message.content)
            if not content:
                raise InvalidResponseError(self.name, reason="empty response body")
            return content
        except (ProviderUnavailableError, InvalidResponseError):
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "timeout" in msg or "timed out" in msg:
                raise ProviderTimeoutError(self.name, timeout=120) from exc
            raise LLMError(
                f"xAI generation failed: {exc}",
                context={"provider": self.name, "model": self.model_name},
            ) from exc

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        return importlib.util.find_spec("openai") is not None

    @property
    def name(self) -> str:
        return "grok"

    @property
    def display_name(self) -> str:
        return "Grok (xAI)"

    @property
    def model_name(self) -> str:
        return "grok-beta"


# ─── PROVIDER REGISTRY ────────────────────────────────────────────────────────


PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "gpt4": OpenAIProvider,
    "groq": GroqProvider,
    "grok": XAIProvider,
    "ollama": OllamaProvider,
}


# ─── ERROR RECOVERY ───────────────────────────────────────────────────────────


def generate_with_retry(
    provider: LLMProvider,
    prompt: str,
    system_prompt: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
) -> str:
    """Call provider.generate() with exponential backoff on transient errors.

    Retry schedule: attempt 1 → wait 1s → attempt 2 → wait 2s → attempt 3 → fail.

    Args:
        provider: Initialized LLM provider.
        prompt: User's generation request.
        system_prompt: System instructions for the LLM.
        max_retries: Maximum number of attempts (default: 3).
        backoff_base: Base wait time in seconds, doubles each retry (default: 1.0).

    Returns:
        Generated markdown content.

    Raises:
        LLMError: After all retries exhausted or on non-retryable error.
    """
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Generating with %s (attempt %d/%d)",
                provider.display_name,
                attempt,
                max_retries,
            )
            result = provider.generate(prompt, system_prompt)
            if attempt > 1:
                logger.info(
                    "Generation succeeded on attempt %d for %s",
                    attempt,
                    provider.display_name,
                )
            return result

        except LLMError as exc:
            last_error = exc
            if not _is_retryable(exc):
                logger.error(
                    "Non-retryable error from %s: %s",
                    provider.display_name,
                    exc,
                )
                raise

            if attempt < max_retries:
                wait = backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "Transient error from %s (attempt %d/%d), retrying in %.1fs: %s",
                    provider.display_name,
                    attempt,
                    max_retries,
                    wait,
                    exc,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "All %d attempts failed for %s: %s",
                    max_retries,
                    provider.display_name,
                    exc,
                )

        except Exception as exc:
            # Non-LLMError (e.g. ImportError) — wrap and re-raise immediately
            logger.error("Unexpected error from %s: %s", provider.display_name, exc)
            raise LLMError(
                f"Unexpected error: {exc}",
                context={"provider": provider.name},
            ) from exc

    raise LLMError(
        f"Generation failed after {max_retries} attempts",
        context={"provider": provider.name, "last_error": str(last_error)},
    )


def generate_with_fallback(
    prompt: str,
    system_prompt: str,
    preferred: Optional[str] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Tuple[str, str]:
    """Generate content, falling back through available providers on failure.

    Tries ``preferred`` first (with retries), then each provider in
    FALLBACK_ORDER until one succeeds.

    Args:
        prompt: User's generation request.
        system_prompt: System instructions for the LLM.
        preferred: Provider name to try first. None = auto-select by priority.
        max_retries: Retry attempts per provider (default: 3).

    Returns:
        Tuple of (generated_content, provider_name_used).

    Raises:
        LLMError: If all available providers fail.
    """
    candidates: List[str] = []

    if preferred and preferred != "auto":
        if preferred not in PROVIDERS:
            raise LLMError(
                f"Unknown provider: {preferred}",
                context={"available": list(PROVIDERS.keys())},
            )
        candidates.append(preferred)

    for name in FALLBACK_ORDER:
        if name not in candidates:
            candidates.append(name)

    errors: Dict[str, str] = {}

    for name in candidates:
        provider_class = PROVIDERS[name]
        provider = provider_class()

        if not provider.is_available():
            logger.debug("Skipping %s — not available", provider.display_name)
            continue

        try:
            content = generate_with_retry(provider, prompt, system_prompt, max_retries=max_retries)
            logger.info("Successfully generated with %s", provider.display_name)
            return content, name

        except LLMError as exc:
            errors[name] = str(exc)
            logger.warning(
                "Provider %s failed, trying next fallback: %s",
                provider.display_name,
                exc,
            )

    raise LLMError(
        "All providers failed",
        context={"errors": errors, "tried": list(errors.keys())},
    )


# ─── PROVIDER SELECTION ───────────────────────────────────────────────────────


def get_provider(name: str = "auto") -> LLMProvider:
    """Get LLM provider by name or auto-select first available.

    Args:
        name: Provider name ('claude', 'gemini', 'gpt4', 'groq', 'grok',
              'ollama', or 'auto').

    Returns:
        Initialized provider instance.

    Raises:
        ProviderUnavailableError: If provider not found or not available.
    """
    if name == "auto":
        for provider_name in FALLBACK_ORDER:
            provider_class = PROVIDERS[provider_name]
            provider = provider_class()
            if provider.is_available():
                return provider
        raise ProviderUnavailableError(
            "auto",
            reason=(
                "No LLM providers available. Set API keys: "
                "GROQ_API_KEY, XAI_API_KEY, ANTHROPIC_API_KEY, "
                "GOOGLE_API_KEY, OPENAI_API_KEY, or run Ollama."
            ),
        )

    if name not in PROVIDERS:
        raise ProviderUnavailableError(
            name,
            reason=f"Unknown provider. Available: {', '.join(PROVIDERS.keys())}",
        )

    provider_class = PROVIDERS[name]
    provider = provider_class()

    if not provider.is_available():
        raise ProviderUnavailableError(
            name,
            reason=f"Check API key and dependencies for {provider.display_name}.",
        )

    return provider


def list_providers() -> Dict[str, bool]:
    """List all providers and their availability status.

    Returns:
        Dict mapping provider name to availability boolean.
    """
    return {name: cls().is_available() for name, cls in PROVIDERS.items()}
