"""Unit tests for akf generate --batch (v0.5.3).

Tests:
  - test_batch_json_valid_plan       — valid plan.json runs successfully
  - test_batch_json_invalid_plan     — malformed JSON exits with error
  - test_batch_partial_failure       — some items fail → exit code 1
  - test_batch_empty_plan            — empty array → no-op, exit code 0
"""

import json
import sys
import pytest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from akf.pipeline import GenerateResult

# ─── helpers ──────────────────────────────────────────────────────────────────


def _make_result(success: bool, path: Path, attempts: int = 1) -> GenerateResult:
    return GenerateResult(
        success=success,
        content="",
        file_path=path,
        attempts=attempts,
        errors=[] if success else ["E005 domain mismatch"],
        generation_id="gen-test",
        duration_ms=10,
    )


def _args(batch_path, output_dir, model="auto"):
    return Namespace(batch=str(batch_path), output=str(output_dir), model=model, prompt=None)


# ─── test_batch_json_valid_plan ───────────────────────────────────────────────


class TestBatchJsonValidPlan:
    def test_batch_json_valid_plan(self, tmp_path, capsys):
        """Valid plan.json with two items → both succeed → exit 0."""
        plan = [
            {"prompt": "AKF pipeline architecture", "domain": "akf-core", "type": "reference"},
            {"prompt": "AKF CLI reference", "domain": "akf-docs", "type": "guide"},
        ]
        plan_file = tmp_path / "plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        mock_results = [
            _make_result(True, tmp_path / "akf-pipeline-architecture.md", attempts=1),
            _make_result(True, tmp_path / "akf-cli-reference.md", attempts=1),
        ]

        with patch("akf.pipeline.Pipeline") as MockPipeline:
            MockPipeline.return_value.batch_generate.return_value = mock_results
            args = _args(plan_file, tmp_path)
            with pytest.raises(SystemExit) as exc:
                from cli import _cmd_generate_batch

                _cmd_generate_batch(args)

        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "Total: 2 | OK: 2 | Failed: 0" in captured.out

    def test_batch_passes_dict_hints_to_pipeline(self, tmp_path):
        """Dict items (with domain/type) are forwarded as-is to batch_generate."""
        plan = [{"prompt": "Test", "domain": "devops", "type": "guide"}]
        plan_file = tmp_path / "plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        mock_results = [_make_result(True, tmp_path / "test.md")]

        with patch("akf.pipeline.Pipeline") as MockPipeline:
            MockPipeline.return_value.batch_generate.return_value = mock_results
            args = _args(plan_file, tmp_path)
            with pytest.raises(SystemExit):
                from cli import _cmd_generate_batch

                _cmd_generate_batch(args)

            call_args = MockPipeline.return_value.batch_generate.call_args
            passed_plan = call_args[0][0]  # first positional arg
            assert passed_plan == plan


# ─── test_batch_json_invalid_plan ─────────────────────────────────────────────


class TestBatchJsonInvalidPlan:
    def test_batch_json_invalid_plan(self, tmp_path):
        """Malformed JSON exits with code 1 and prints an error."""
        plan_file = tmp_path / "bad.json"
        plan_file.write_text("{not valid json", encoding="utf-8")

        args = _args(plan_file, tmp_path)
        with pytest.raises(SystemExit) as exc:
            from cli import _cmd_generate_batch

            _cmd_generate_batch(args)

        assert exc.value.code == 1

    def test_batch_json_not_array(self, tmp_path):
        """JSON object (not array) exits with code 1."""
        plan_file = tmp_path / "obj.json"
        plan_file.write_text(json.dumps({"prompt": "single"}), encoding="utf-8")

        args = _args(plan_file, tmp_path)
        with pytest.raises(SystemExit) as exc:
            from cli import _cmd_generate_batch

            _cmd_generate_batch(args)

        assert exc.value.code == 1

    def test_batch_json_missing_file(self, tmp_path):
        """Non-existent plan file exits with code 1."""
        args = _args(tmp_path / "nonexistent.json", tmp_path)
        with pytest.raises(SystemExit) as exc:
            from cli import _cmd_generate_batch

            _cmd_generate_batch(args)

        assert exc.value.code == 1


# ─── test_batch_partial_failure ───────────────────────────────────────────────


class TestBatchPartialFailure:
    def test_batch_partial_failure(self, tmp_path, capsys):
        """One item succeeds, one fails → exit code 1, both shown."""
        plan = [
            {"prompt": "AKF pipeline architecture", "domain": "akf-core", "type": "reference"},
            {"prompt": "AKF CLI reference", "domain": "akf-docs", "type": "guide"},
        ]
        plan_file = tmp_path / "plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        mock_results = [
            _make_result(True, tmp_path / "akf-pipeline-architecture.md", attempts=1),
            _make_result(False, tmp_path / "akf-cli-reference.md", attempts=3),
        ]

        with patch("akf.pipeline.Pipeline") as MockPipeline:
            MockPipeline.return_value.batch_generate.return_value = mock_results
            args = _args(plan_file, tmp_path)
            with pytest.raises(SystemExit) as exc:
                from cli import _cmd_generate_batch

                _cmd_generate_batch(args)

        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "❌" in captured.out
        assert "Total: 2 | OK: 1 | Failed: 1" in captured.out

    def test_batch_all_fail(self, tmp_path):
        """All items fail → exit code 1."""
        plan = [{"prompt": "Bad prompt 1"}, {"prompt": "Bad prompt 2"}]
        plan_file = tmp_path / "plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        mock_results = [
            _make_result(False, tmp_path / "bad-prompt-1.md", attempts=3),
            _make_result(False, tmp_path / "bad-prompt-2.md", attempts=3),
        ]

        with patch("akf.pipeline.Pipeline") as MockPipeline:
            MockPipeline.return_value.batch_generate.return_value = mock_results
            args = _args(plan_file, tmp_path)
            with pytest.raises(SystemExit) as exc:
                from cli import _cmd_generate_batch

                _cmd_generate_batch(args)

        assert exc.value.code == 1


# ─── test_batch_empty_plan ────────────────────────────────────────────────────


class TestBatchEmptyPlan:
    def test_batch_empty_plan(self, tmp_path, capsys):
        """Empty JSON array → exit 0, no pipeline calls."""
        plan_file = tmp_path / "empty.json"
        plan_file.write_text("[]", encoding="utf-8")

        with patch("akf.pipeline.Pipeline") as MockPipeline:
            args = _args(plan_file, tmp_path)
            with pytest.raises(SystemExit) as exc:
                from cli import _cmd_generate_batch

                _cmd_generate_batch(args)

        assert exc.value.code == 0
        MockPipeline.return_value.batch_generate.assert_not_called()
        captured = capsys.readouterr()
        assert "Total: 0 | OK: 0 | Failed: 0" in captured.out
