"""
Tests — S3: Retry Controller
AKF Phase 2.1 / ADR-001

Coverage targets:
  - Immediate success: no blocking errors on first pass → 0 LLM calls
  - Convergence on retry: LLM fixes error → success
  - Identical output abort: LLM returns same doc twice → abort
  - Convergence failure: same (field, E-code) on consecutive attempts → abort
  - max_attempts exhausted: LLM never fixes → abort with reason
  - _check_convergence: direct unit tests
  - _hash: deterministic
"""

import pytest
from akf.retry_controller import (
    run_retry_loop,
    RetryResult,
    _check_convergence,
    _hash,
    MAX_ATTEMPTS,
)
from akf.validation_error import (
    ValidationError,
    ErrorCode,
    Severity,
    missing_field,
    invalid_enum,
    taxonomy_violation,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

VALID_DOC = """\
---
title: Test
schema_version: "1.0.0"
---
body
"""

INVALID_DOC = """\
---
title: Test
domain: backend
---
body
"""

FIXED_DOC = """\
---
title: Test
domain: api-design
schema_version: "1.0.0"
---
body
"""


def domain_error(received: str = "backend") -> ValidationError:
    return taxonomy_violation("domain", received, ["api-design", "devops"])


def _gen_always_valid(doc: str, prompt: str) -> str:
    return FIXED_DOC


def _gen_always_same(doc: str, prompt: str) -> str:
    return INVALID_DOC  # always returns the same broken doc


def _validate_valid(doc: str) -> list[ValidationError]:
    return []


def _validate_invalid(doc: str) -> list[ValidationError]:
    return [domain_error()]


# ── Immediate success ─────────────────────────────────────────────────────────


class TestImmediateSuccess:

    def test_no_errors_returns_success_with_zero_attempts(self):
        result = run_retry_loop(
            document=VALID_DOC,
            errors=[],
            generate_fn=_gen_always_valid,
            validate_fn=_validate_valid,
        )
        assert result.success is True
        assert result.attempts == 0
        assert result.document == VALID_DOC
        assert result.abort_reason is None

    def test_warnings_only_treated_as_no_blocking(self):
        warning = ValidationError(
            code=ErrorCode.SCHEMA_VIOLATION,
            field="title",
            expected="x",
            received="y",
            severity=Severity.WARNING,
        )
        result = run_retry_loop(
            document=VALID_DOC,
            errors=[warning],
            generate_fn=_gen_always_valid,
            validate_fn=_validate_valid,
        )
        assert result.success is True
        assert result.attempts == 0


# ── Convergence on retry ──────────────────────────────────────────────────────


class TestConvergenceOnRetry:

    def test_fixed_on_first_retry(self):
        call_count = {"n": 0}

        def gen(doc: str, prompt: str) -> str:
            call_count["n"] += 1
            return FIXED_DOC

        def validate(doc: str) -> list[ValidationError]:
            if doc == FIXED_DOC:
                return []
            return [domain_error()]

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[domain_error()],
            generate_fn=gen,
            validate_fn=validate,
        )
        assert result.success is True
        assert result.attempts == 1
        assert call_count["n"] == 1
        assert result.document == FIXED_DOC

    def test_fixed_on_second_retry(self):
        """
        Attempt 1: LLM returns a doc with a *different* error (level instead of domain).
        Attempt 2: LLM fixes everything → success.
        Consecutive different fields → no convergence abort.
        """
        INTERMEDIATE = """\
---
title: Test
domain: api-design
level: expert
schema_version: "1.0.0"
---
body
"""
        gen_calls = {"n": 0}

        def gen(doc: str, prompt: str) -> str:
            gen_calls["n"] += 1
            if gen_calls["n"] == 1:
                return INTERMEDIATE
            return FIXED_DOC

        def validate(doc: str) -> list[ValidationError]:
            if doc == FIXED_DOC:
                return []
            if doc == INTERMEDIATE:
                return [invalid_enum("level", ["beginner", "intermediate", "advanced"], "expert")]
            return [domain_error()]

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[domain_error()],
            generate_fn=gen,
            validate_fn=validate,
        )
        assert result.success is True
        assert result.attempts == 2

    def test_prompt_passed_to_generate_fn(self):
        received_prompts = []

        def gen(doc: str, prompt: str) -> str:
            received_prompts.append(prompt)
            return FIXED_DOC

        run_retry_loop(
            document=INVALID_DOC,
            errors=[domain_error()],
            generate_fn=gen,
            validate_fn=_validate_valid,
        )
        assert len(received_prompts) == 1
        assert "VALIDATION ERRORS" in received_prompts[0]


# ── Identical output abort ────────────────────────────────────────────────────


class TestIdenticalOutputAbort:

    def test_same_doc_twice_aborts_with_identical_output(self):
        """
        To reach the hash check, consecutive errors must have different (field, code)
        so convergence doesn't abort first.
        Attempt 1: gen → doc_A, error on field 'domain' (different from initial field 'level')
        Attempt 2: gen → doc_A again (same hash) → identical_output abort
        """
        INITIAL_ERROR = invalid_enum("level", ["beginner", "advanced"], "expert")
        DOMAIN_ERR = domain_error()
        DOC_A = INVALID_DOC + " #1"

        gen_calls = {"n": 0}

        def gen(doc: str, prompt: str) -> str:
            gen_calls["n"] += 1
            return DOC_A  # always return same content

        def validate(doc: str) -> list[ValidationError]:
            return [DOMAIN_ERR]  # always domain error

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[INITIAL_ERROR],  # initial error is 'level' — different field
            generate_fn=gen,
            validate_fn=validate,
        )
        assert result.success is False
        # Attempt 1: DOC_A generated, hash stored, domain error — diff field from level → ok
        # Attempt 2: DOC_A generated, hash match → identical_output
        assert "identical_output" in result.abort_reason

    def test_abort_reason_set_on_identical(self):
        INITIAL_ERROR = invalid_enum("level", ["beginner", "advanced"], "expert")
        DOC_A = INVALID_DOC + " constant"

        def gen(doc: str, prompt: str) -> str:
            return DOC_A

        def validate(doc: str) -> list[ValidationError]:
            return [domain_error()]  # different field from initial 'level'

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[INITIAL_ERROR],
            generate_fn=gen,
            validate_fn=validate,
        )
        assert result.abort_reason is not None
        assert "identical_output" in result.abort_reason


# ── Convergence failure (same field+code twice) ───────────────────────────────


class TestConvergenceFailure:

    def test_same_field_code_consecutive_aborts(self):
        """LLM returns new text each time but same field keeps failing."""
        counter = {"n": 0}

        def gen(doc: str, prompt: str) -> str:
            counter["n"] += 1
            return INVALID_DOC + f"\n# attempt {counter['n']}"

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[domain_error()],
            generate_fn=gen,
            validate_fn=_validate_invalid,
        )
        assert result.success is False
        assert "convergence_failure" in result.abort_reason

    def test_convergence_failure_abort_reason_contains_field(self):
        counter = {"n": 0}

        def gen(doc: str, prompt: str) -> str:
            counter["n"] += 1
            return INVALID_DOC + f" #{counter['n']}"

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[domain_error()],
            generate_fn=gen,
            validate_fn=_validate_invalid,
        )
        assert "domain" in result.abort_reason

    def test_different_field_code_does_not_abort(self):
        """
        Initial error: level (E001). Attempt 1: domain error (E006). Attempt 2: type error (E001/type).
        Each consecutive pair has different (field, code) → convergence never fires.
        With max_attempts=2 and 2 attempts both failing, abort with max_attempts_reached.
        """
        errors_sequence = [
            [domain_error()],  # attempt 1: different field from initial 'level'
            [invalid_enum("type", ["concept", "guide"], "article")],  # attempt 2: different field
        ]
        gen_calls = {"n": 0}

        def gen(doc: str, prompt: str) -> str:
            n = gen_calls["n"]
            gen_calls["n"] += 1
            return INVALID_DOC + f" attempt_{n}"

        def validate(doc: str) -> list[ValidationError]:
            # Map attempt index to the doc suffix
            for i, suffix in enumerate([" attempt_0", " attempt_1"]):
                if doc.endswith(suffix):
                    return errors_sequence[i]
            return []

        initial_error = invalid_enum("level", ["beginner", "advanced"], "expert")
        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[initial_error],
            generate_fn=gen,
            validate_fn=validate,
            max_attempts=2,
        )
        assert "convergence_failure" not in (result.abort_reason or "")


# ── max_attempts exhaustion ───────────────────────────────────────────────────


class TestMaxAttempts:

    def test_never_fixes_exhausts_max_attempts(self):
        counter = {"n": 0}

        def gen(doc: str, prompt: str) -> str:
            counter["n"] += 1
            # Each doc is unique (avoids identical_output abort)
            return INVALID_DOC + f"\n# unique {counter['n']}"

        def validate(doc: str) -> list[ValidationError]:
            # Different field each time — avoids convergence failure
            fields = ["domain", "level", "type"]
            return [missing_field(fields[min(counter["n"] - 1, 2)])]

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[domain_error()],
            generate_fn=gen,
            validate_fn=validate,
            max_attempts=3,
        )
        assert result.success is False
        assert result.attempts == 3
        assert "max_attempts" in result.abort_reason

    def test_custom_max_attempts_respected(self):
        counter = {"n": 0}

        def gen(doc: str, prompt: str) -> str:
            counter["n"] += 1
            return INVALID_DOC + f" #{counter['n']}"

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[domain_error()],
            generate_fn=gen,
            validate_fn=_validate_invalid,
            max_attempts=1,
        )
        # With max_attempts=1, should abort at convergence or max_attempts
        assert result.success is False

    def test_default_max_attempts_is_3(self):
        assert MAX_ATTEMPTS == 3


# ── _check_convergence direct tests ──────────────────────────────────────────


class TestCheckConvergence:

    def test_same_field_and_code_returns_abort_reason(self):
        prev = [taxonomy_violation("domain", "backend", ["api-design"])]
        curr = [taxonomy_violation("domain", "cloud", ["api-design"])]  # same code+field
        result = _check_convergence(prev, curr)
        assert result is not None
        assert "convergence_failure" in result
        assert "domain" in result

    def test_different_field_returns_none(self):
        prev = [missing_field("domain")]
        curr = [missing_field("type")]
        result = _check_convergence(prev, curr)
        assert result is None

    def test_different_code_same_field_returns_none(self):
        prev = [missing_field("domain")]
        curr = [taxonomy_violation("domain", "backend", [])]
        result = _check_convergence(prev, curr)
        assert result is None

    def test_empty_lists_return_none(self):
        assert _check_convergence([], []) is None

    def test_prev_empty_returns_none(self):
        assert _check_convergence([], [missing_field("domain")]) is None


# ── _hash determinism ─────────────────────────────────────────────────────────


class TestHash:

    def test_same_text_same_hash(self):
        assert _hash("hello") == _hash("hello")

    def test_different_text_different_hash(self):
        assert _hash("hello") != _hash("world")

    def test_hash_is_64_char_hex(self):
        h = _hash("any string")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
