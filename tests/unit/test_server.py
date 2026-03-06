"""Unit tests for AKF REST API (Stage 3)."""

import os
import textwrap
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from akf.server import app, verify_key
from akf.pipeline import GenerateResult, ValidateResult
from pathlib import Path

# ─── FIXTURES ─────────────────────────────────────────────────────────────────

def _no_auth():
    """Override verify_key — skip auth in most tests."""
    return None


@pytest.fixture(autouse=True)
def disable_auth():
    """Disable auth by default for all tests."""
    app.dependency_overrides[verify_key] = _no_auth
    yield
    app.dependency_overrides.clear()


client = TestClient(app, raise_server_exceptions=True)

VALID_CONTENT = textwrap.dedent("""\
    ---
    schema_version: "1.0.0"
    title: "Test Guide"
    type: guide
    domain: devops
    level: intermediate
    status: active
    tags: [docker, guide, test]
    related:
      - "[[Docker Basics]]"
    created: 2026-02-26
    updated: 2026-02-26
    ---

    ## Purpose

    Test content.

    ## Conclusion

    Done.
""")


def _make_result(success=True, idx=0):
    return GenerateResult(
        success=success,
        content=VALID_CONTENT,
        file_path=Path(f"/tmp/test_{idx}.md"),
        attempts=1,
        errors=[],
        generation_id=f"test-uuid-{idx}",
        duration_ms=100,
    )


# ─── HEALTH ───────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_version(self):
        r = client.get("/health")
        assert "version" in r.json()

    def test_health_no_auth_required(self):
        """Health endpoint is always public (no auth dependency)."""
        app.dependency_overrides.clear()  # restore real verify_key
        r = client.get("/health")
        assert r.status_code == 200
        app.dependency_overrides[verify_key] = _no_auth  # re-disable for other tests


# ─── AUTH ─────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_no_key_configured_allows_access(self):
        """When AKF_API_KEY not set, auth is disabled — all requests pass."""
        app.dependency_overrides.clear()  # use real verify_key
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AKF_API_KEY", None)
            # Reload the key from env
            import importlib
            import akf.server as srv
            srv._AKF_API_KEY = None
            r = client.get("/v1/models")
        assert r.status_code in (200, 422)  # not 401

    def test_valid_key_grants_access(self):
        """Correct Bearer token grants access."""
        app.dependency_overrides.clear()
        import akf.server as srv
        srv._AKF_API_KEY = "test-secret-key"
        with patch("llm_providers.list_providers", return_value={}):
            r = client.get(
                "/v1/models",
                headers={"Authorization": "Bearer test-secret-key"},
            )
        assert r.status_code == 200
        srv._AKF_API_KEY = None
        app.dependency_overrides[verify_key] = _no_auth

    def test_wrong_key_returns_401(self):
        """Wrong token returns 401."""
        app.dependency_overrides.clear()
        import akf.server as srv
        srv._AKF_API_KEY = "correct-key"
        r = client.get(
            "/v1/models",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert r.status_code == 401
        srv._AKF_API_KEY = None
        app.dependency_overrides[verify_key] = _no_auth

    def test_missing_token_returns_401(self):
        """No Authorization header returns 401 when key is configured."""
        app.dependency_overrides.clear()
        import akf.server as srv
        srv._AKF_API_KEY = "some-key"
        r = client.get("/v1/models")
        assert r.status_code == 401
        srv._AKF_API_KEY = None
        app.dependency_overrides[verify_key] = _no_auth


# ─── MODELS ───────────────────────────────────────────────────────────────────

class TestModels:
    def test_models_returns_providers(self):
        with patch("llm_providers.list_providers", return_value={"claude": False, "groq": False}):
            r = client.get("/v1/models")
        assert r.status_code == 200
        assert "providers" in r.json()


# ─── GENERATE ─────────────────────────────────────────────────────────────────

class TestGenerate:
    def test_generate_success(self):
        with patch("akf.server.get_pipeline") as mock_get:
            mock_get.return_value.generate.return_value = _make_result(True)
            r = client.post("/v1/generate", json={"prompt": "Create a guide"})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["attempts"] == 1
        assert data["generation_id"] == "test-uuid-0"

    def test_generate_failure(self):
        with patch("akf.server.get_pipeline") as mock_get:
            mock_get.return_value.generate.return_value = _make_result(False)
            r = client.post("/v1/generate", json={"prompt": "Create a guide"})
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_generate_with_model(self):
        with patch("akf.server.get_pipeline") as mock_get:
            mock_get.return_value.generate.return_value = _make_result()
            r = client.post("/v1/generate", json={"prompt": "Test", "model": "groq"})
        assert r.status_code == 200

    def test_generate_missing_prompt(self):
        r = client.post("/v1/generate", json={})
        assert r.status_code == 422

    def test_generate_empty_prompt(self):
        r = client.post("/v1/generate", json={"prompt": ""})
        assert r.status_code == 422

    def test_generate_prompt_too_long(self):
        r = client.post("/v1/generate", json={"prompt": "x" * 2001})
        assert r.status_code == 422

    def test_generate_prompt_max_length_ok(self):
        with patch("akf.server.get_pipeline") as mock_get:
            mock_get.return_value.generate.return_value = _make_result()
            r = client.post("/v1/generate", json={"prompt": "x" * 2000})
        assert r.status_code == 200

    def test_generate_path_in_response(self):
        with patch("akf.server.get_pipeline") as mock_get:
            mock_get.return_value.generate.return_value = _make_result()
            r = client.post("/v1/generate", json={"prompt": "Test"})
        assert r.json()["path"] is not None


# ─── VALIDATE ─────────────────────────────────────────────────────────────────

class TestValidate:
    def test_validate_valid_content(self):
        r = client.post("/v1/validate", json={"content": VALID_CONTENT})
        assert r.status_code == 200
        data = r.json()
        assert "valid" in data
        assert "errors" in data
        assert "warnings" in data

    def test_validate_invalid_content(self):
        bad = "---\ntitle: x\ntype: bad\n---\n## Content"
        r = client.post("/v1/validate", json={"content": bad})
        assert r.status_code == 200
        assert r.json()["valid"] is False

    def test_validate_strict_mode(self):
        r = client.post("/v1/validate", json={"content": VALID_CONTENT, "strict": True})
        assert r.status_code == 200

    def test_validate_missing_content(self):
        r = client.post("/v1/validate", json={})
        assert r.status_code == 422

    def test_validate_empty_content(self):
        r = client.post("/v1/validate", json={"content": ""})
        assert r.status_code == 422


# ─── BATCH ────────────────────────────────────────────────────────────────────

class TestBatch:
    def test_batch_success(self):
        with patch("akf.server.get_pipeline") as mock_get:
            mock_get.return_value.batch_generate.return_value = [
                _make_result(True, 0), _make_result(True, 1)
            ]
            r = client.post("/v1/batch", json={"prompts": ["Guide 1", "Guide 2"]})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["success"] == 2
        assert data["failed"] == 0
        assert len(data["results"]) == 2

    def test_batch_empty(self):
        with patch("akf.server.get_pipeline") as mock_get:
            mock_get.return_value.batch_generate.return_value = []
            r = client.post("/v1/batch", json={"prompts": []})
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_batch_missing_prompts(self):
        r = client.post("/v1/batch", json={})
        assert r.status_code == 422

    def test_batch_too_many_prompts(self):
        r = client.post("/v1/batch", json={"prompts": [f"Prompt {i}" for i in range(21)]})
        assert r.status_code == 422

    def test_batch_max_prompts_ok(self):
        with patch("akf.server.get_pipeline") as mock_get:
            mock_get.return_value.batch_generate.return_value = [
                _make_result(True, i) for i in range(20)
            ]
            r = client.post("/v1/batch", json={"prompts": [f"Prompt {i}" for i in range(20)]})
        assert r.status_code == 200
        assert r.json()["total"] == 20
