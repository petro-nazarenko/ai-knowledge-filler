"""Tests for exceptions.py — AKF exception hierarchy."""

import pytest
from exceptions import (
    AKFError,
    ValidationError,
    MissingFieldError,
    InvalidFieldValueError,
    InvalidDomainError,
    LLMError,
    ProviderUnavailableError,
    ProviderTimeoutError,
    InvalidResponseError,
    ConfigError,
    MissingConfigError,
    InvalidConfigError,
    FileError,
    AKFFileNotFoundError,
    FileParseError,
)


def test_akf_error_basic():
    e = AKFError("base error")
    assert str(e) == "base error"


def test_akf_error_with_context():
    e = AKFError("error", context={"key": "val"})
    assert "key=val" in str(e)


def test_akf_error_empty_context():
    e = AKFError("no ctx", context=None)
    assert str(e) == "no ctx"


def test_missing_field_error():
    e = MissingFieldError("title", "file.md")
    assert "title" in str(e)
    assert e.context["field"] == "title"
    assert e.context["file"] == "file.md"


def test_missing_field_no_filepath():
    e = MissingFieldError("domain")
    assert e.context["file"] == ""


def test_invalid_field_value_error():
    e = InvalidFieldValueError("type", "doc", ["concept", "guide"])
    assert "doc" in str(e)
    assert e.context["allowed"] == ["concept", "guide"]


def test_invalid_domain_error():
    e = InvalidDomainError("Tech", suggestion="system-design")
    assert "Tech" in str(e)
    assert e.context["suggestion"] == "system-design"


def test_invalid_domain_no_suggestion():
    e = InvalidDomainError("unknown")
    assert "suggestion" not in e.context


def test_provider_unavailable_error():
    e = ProviderUnavailableError("claude")
    assert "claude" in str(e)
    assert e.context["provider"] == "claude"


def test_provider_timeout_error():
    e = ProviderTimeoutError("gemini", 30.0)
    assert "30" in str(e)
    assert e.context["timeout"] == 30.0


def test_invalid_response_error():
    e = InvalidResponseError("gpt4", reason="empty response")
    assert e.context["reason"] == "empty response"


def test_missing_config_error():
    e = MissingConfigError("API_KEY")
    assert "API_KEY" in str(e)


def test_file_not_found_error():
    e = AKFFileNotFoundError("/path/to/file.md")
    assert "/path/to/file.md" in str(e)


def test_file_parse_error():
    e = FileParseError("bad.md", reason="invalid yaml")
    assert e.context["reason"] == "invalid yaml"


def test_inheritance_chain():
    assert issubclass(MissingFieldError, ValidationError)
    assert issubclass(ValidationError, AKFError)
    assert issubclass(ProviderUnavailableError, LLMError)
    assert issubclass(LLMError, AKFError)
    assert issubclass(AKFFileNotFoundError, FileError)
    assert issubclass(FileError, AKFError)


def test_exceptions_are_catchable():
    with pytest.raises(AKFError):
        raise MissingFieldError("title")

    with pytest.raises(ValidationError):
        raise InvalidDomainError("bad")
