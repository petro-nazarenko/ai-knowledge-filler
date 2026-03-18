"""Tests for logger.py — JSONFormatter and get_logger."""

import json
import logging
import pytest
from logger import JSONFormatter, get_logger


def test_get_logger_returns_logger():
    logger = get_logger("test_basic")
    assert isinstance(logger, logging.Logger)


def test_get_logger_singleton():
    a = get_logger("test_singleton")
    b = get_logger("test_singleton")
    assert a is b


def test_get_logger_no_duplicate_handlers():
    get_logger("test_handlers")
    get_logger("test_handlers")
    logger = logging.getLogger("test_handlers")
    assert len(logger.handlers) == 1


def test_json_formatter_output(capfd):
    logger = get_logger("test_json", json_output=True)
    logger.info("hello json")
    out = capfd.readouterr().out.strip()
    obj = json.loads(out)
    assert obj["level"] == "INFO"
    assert obj["message"] == "hello json"
    assert "timestamp" in obj
    assert "module" in obj


def test_json_formatter_exception(capfd):
    logger = get_logger("test_exc_json", json_output=True)
    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("caught")
    out = capfd.readouterr().out.strip()
    obj = json.loads(out)
    assert "exception" in obj
    assert "ValueError" in obj["exception"]


def test_human_formatter_no_json(capfd):
    logger = get_logger("test_human", json_output=False)
    logger.warning("plain warning")
    out = capfd.readouterr().out.strip()
    # Should NOT be JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)


def test_log_level_respected(capfd):
    logger = get_logger("test_level", level="ERROR", json_output=True)
    logger.info("should not appear")
    out = capfd.readouterr().out.strip()
    assert out == ""


def test_json_formatter_directly():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0, msg="direct", args=(), exc_info=None
    )
    result = json.loads(formatter.format(record))
    assert result["message"] == "direct"
    assert result["level"] == "INFO"
