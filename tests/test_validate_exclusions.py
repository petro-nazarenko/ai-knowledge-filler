"""Tests for file exclusion logic in validate_yaml and cli.

Mirrors EXCLUDE_PATTERNS from validate_yaml.py and cli.py cmd_validate()
without touching the filesystem — pure logic tests.
"""

# ── Patterns (mirror production) ─────────────────────────────────────────────

VALIDATE_YAML_PATTERNS = [
    ".github",
    "README.md",
    "CONTRIBUTING.md",
    "ARCHITECTURE.md",
    "08-TEMPLATES",
]

CLI_PATTERNS = [
    ".github",
    "README.md",
    "08-TEMPLATES",
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def apply_exclusion(files: list[str], patterns: list[str]) -> list[str]:
    return [f for f in files if not any(x in f for x in patterns)]


# ── validate_yaml exclusion tests ─────────────────────────────────────────────


class TestValidateYamlExclusions:
    def test_templates_root_excluded(self):
        assert apply_exclusion(["08-TEMPLATES/foo.md"], VALIDATE_YAML_PATTERNS) == []

    def test_templates_nested_excluded(self):
        assert apply_exclusion(["vault/0_AKF/08-TEMPLATES/daily.md"], VALIDATE_YAML_PATTERNS) == []

    def test_github_excluded(self):
        assert apply_exclusion([".github/PULL_REQUEST_TEMPLATE.md"], VALIDATE_YAML_PATTERNS) == []

    def test_readme_excluded(self):
        assert apply_exclusion(["README.md"], VALIDATE_YAML_PATTERNS) == []

    def test_contributing_excluded(self):
        assert apply_exclusion(["docs/CONTRIBUTING.md"], VALIDATE_YAML_PATTERNS) == []

    def test_architecture_excluded(self):
        assert apply_exclusion(["docs/ARCHITECTURE.md"], VALIDATE_YAML_PATTERNS) == []

    def test_canon_included(self):
        files = ["01-CANON/AKF_Canon.md"]
        assert apply_exclusion(files, VALIDATE_YAML_PATTERNS) == files

    def test_adr_included(self):
        files = ["05-ADR/ADR-001.md"]
        assert apply_exclusion(files, VALIDATE_YAML_PATTERNS) == files

    def test_overhead_included(self):
        """10-OVERHEAD included — policy defined in Task 9, not here."""
        files = ["10-OVERHEAD/old_file.md"]
        assert apply_exclusion(files, VALIDATE_YAML_PATTERNS) == files

    def test_all_excluded_paths_removed(self):
        excluded = [
            "08-TEMPLATES/some_template.md",
            "vault/08-TEMPLATES/daily_note.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            "README.md",
            "docs/CONTRIBUTING.md",
            "docs/ARCHITECTURE.md",
        ]
        assert apply_exclusion(excluded, VALIDATE_YAML_PATTERNS) == []

    def test_mixed_list(self):
        excluded = ["08-TEMPLATES/foo.md", "README.md"]
        included = ["01-CANON/AKF_Canon.md", "05-ADR/ADR-001.md"]
        result = apply_exclusion(excluded + included, VALIDATE_YAML_PATTERNS)
        assert result == included


# ── cli.py exclusion tests ────────────────────────────────────────────────────


class TestCliExclusions:
    def test_templates_excluded(self):
        assert apply_exclusion(["08-TEMPLATES/template.md"], CLI_PATTERNS) == []

    def test_templates_nested_excluded(self):
        assert apply_exclusion(["vault/08-TEMPLATES/foo.md"], CLI_PATTERNS) == []

    def test_github_excluded(self):
        assert apply_exclusion([".github/foo.md"], CLI_PATTERNS) == []

    def test_readme_excluded(self):
        assert apply_exclusion(["README.md"], CLI_PATTERNS) == []

    def test_regular_file_included(self):
        files = ["05-ADR/ADR-001.md"]
        assert apply_exclusion(files, CLI_PATTERNS) == files

    def test_mixed_list(self):
        excluded = ["08-TEMPLATES/foo.md", ".github/bar.md"]
        included = ["07-REFERENCE/Domain_Taxonomy.md"]
        result = apply_exclusion(excluded + included, CLI_PATTERNS)
        assert result == included
