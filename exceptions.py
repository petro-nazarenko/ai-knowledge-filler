"""AKF domain exception hierarchy."""

from typing import Any


class AKFError(Exception):
    """Base exception for all AKF errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        if self.context:
            ctx = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{super().__str__()} [{ctx}]"
        return super().__str__()


class ValidationError(AKFError):
    """YAML metadata validation failure."""


class MissingFieldError(ValidationError):
    """Required YAML field is absent."""

    def __init__(self, field: str, filepath: str = "") -> None:
        super().__init__(
            f"Missing required field: '{field}'",
            context={"field": field, "file": filepath},
        )


class InvalidFieldValueError(ValidationError):
    """YAML field contains invalid value."""

    def __init__(self, field: str, value: Any, allowed: list[str]) -> None:
        super().__init__(
            f"Invalid value '{value}' for field '{field}'",
            context={"field": field, "value": value, "allowed": allowed},
        )


class InvalidDomainError(ValidationError):
    """Domain value not in taxonomy."""

    def __init__(self, domain: str, suggestion: str = "") -> None:
        ctx: dict[str, Any] = {"domain": domain}
        if suggestion:
            ctx["suggestion"] = suggestion
        super().__init__(f"Domain '{domain}' not in taxonomy", context=ctx)


class LLMError(AKFError):
    """Base LLM provider error."""


class ProviderUnavailableError(LLMError):
    """LLM provider not reachable or not configured."""

    def __init__(self, provider: str, reason: str = "") -> None:
        ctx: dict[str, Any] = {"provider": provider}
        if reason:
            ctx["reason"] = reason
        super().__init__(
            f"Provider '{provider}' unavailable",
            context=ctx,
        )


class ProviderTimeoutError(LLMError):
    """LLM provider response timed out."""

    def __init__(self, provider: str, timeout: float) -> None:
        super().__init__(
            f"Provider '{provider}' timed out after {timeout}s",
            context={"provider": provider, "timeout": timeout},
        )


class InvalidResponseError(LLMError):
    """LLM response does not contain valid Markdown."""

    def __init__(self, provider: str, reason: str = "") -> None:
        super().__init__(
            f"Invalid response from '{provider}'",
            context={"provider": provider, "reason": reason},
        )


class ConfigError(AKFError):
    """Configuration error."""


class MissingConfigError(ConfigError):
    """Required config key is absent."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Missing config key: '{key}'", context={"key": key})


class InvalidConfigError(ConfigError):
    """Config value is invalid."""


class FileError(AKFError):
    """File operation error."""


class AKFFileNotFoundError(FileError):
    """Target file does not exist."""

    def __init__(self, filepath: str) -> None:
        super().__init__(f"File not found: '{filepath}'", context={"filepath": filepath})


class FileParseError(FileError):
    """File cannot be parsed (YAML, Markdown, etc.)."""

    def __init__(self, filepath: str, reason: str = "") -> None:
        super().__init__(
            f"Cannot parse file: '{filepath}'",
            context={"filepath": filepath, "reason": reason},
        )
