"""Unit tests for validate_yaml.py — updated for Model C (Phase 2.2).

Changes from Model B:
  - domain invalid → E006_TAXONOMY_VIOLATION error (was: warning)
  - All error messages now include E-codes (E001, E002, E003, E004, E006)
"""

import pytest
from Scripts.validate_yaml import validate_file, validate_date_format
import tempfile
import os


class TestDateValidation:
    """Test date format validation"""

    def test_valid_date_format(self):
        assert validate_date_format("2026-02-10") == True
        assert validate_date_format("2024-01-01") == True
        assert validate_date_format("2025-12-31") == True

    def test_invalid_date_format_dd_mm_yyyy(self):
        assert validate_date_format("10-02-2026") == False
        assert validate_date_format("01-01-2024") == False

    def test_invalid_date_format_slashes(self):
        assert validate_date_format("2026/02/10") == False
        assert validate_date_format("10/02/2026") == False

    def test_invalid_date_value(self):
        assert validate_date_format("2026-13-01") == False
        assert validate_date_format("2026-02-30") == False

    def test_invalid_date_feb_30(self):
        assert validate_date_format("2024-02-30") == False


class TestFileValidation:
    """Test validation of complete markdown files"""

    def test_valid_file(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [tag1, tag2, tag3]
created: 2026-02-10
updated: 2026-02-10
---

# Content here
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            assert len(errors) == 0
        finally:
            os.unlink(temp_path)

    def test_missing_frontmatter(self):
        content = """# Just a markdown file\nNo YAML here"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            assert len(errors) == 1
            assert "No YAML frontmatter found" in errors[0]
        finally:
            os.unlink(temp_path)

    def test_missing_title_field(self):
        content = """---
type: guide
domain: ai-system
level: intermediate
status: active
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            # Model C: E002_MISSING_FIELD
            assert any("E002_MISSING_FIELD" in err and "title" in err for err in errors)
        finally:
            os.unlink(temp_path)


class TestMetadataFieldValidation:
    """Test validation of specific metadata fields"""

    def test_invalid_type_field(self):
        content = """---
title: "Test File"
type: document
domain: ai-system
level: intermediate
status: active
tags: [tag1, tag2, tag3]
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            # Model C: E001_INVALID_ENUM
            assert any("E001_INVALID_ENUM" in err and "type" in err for err in errors)
        finally:
            os.unlink(temp_path)

    def test_invalid_level_field(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: medium
status: active
tags: [tag1, tag2, tag3]
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            # Model C: E001_INVALID_ENUM
            assert any("E001_INVALID_ENUM" in err and "level" in err for err in errors)
        finally:
            os.unlink(temp_path)

    def test_invalid_status_field(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
status: in-progress
tags: [tag1, tag2, tag3]
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            # Model C: E001_INVALID_ENUM
            assert any("E001_INVALID_ENUM" in err and "status" in err for err in errors)
        finally:
            os.unlink(temp_path)

    def test_invalid_domain_warning(self):
        """Model C: invalid domain is now an ERROR (E006), not a warning."""
        content = """---
title: "Test File"
type: guide
domain: custom-domain
level: intermediate
status: active
tags: [tag1, tag2, tag3]
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            # Model C: E006_TAXONOMY_VIOLATION — must be error, not warning
            assert any("E006_TAXONOMY_VIOLATION" in err for err in errors)
            assert not any("domain" in w.lower() for w in warnings)
        finally:
            os.unlink(temp_path)

    def test_tags_not_array(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: tag1, tag2, tag3
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            # Model C: E004_TYPE_MISMATCH
            assert any("tags" in err.lower() for err in errors)
        finally:
            os.unlink(temp_path)

    def test_related_not_array(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [tag1, tag2, tag3]
related: "[[Some Link]]"
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            # Model C: E004_TYPE_MISMATCH
            assert any("related" in err.lower() for err in errors)
        finally:
            os.unlink(temp_path)

    def test_insufficient_tags_warning(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [tag1, tag2]
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            assert any("E004_TYPE_MISMATCH" in err and "tags" in err for err in errors)
            assert any("related" in warn for warn in warnings)
        finally:
            os.unlink(temp_path)

    def test_no_related_links_warning(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [tag1, tag2, tag3]
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            assert len(errors) == 0
            assert any("related" in warn for warn in warnings)
        finally:
            os.unlink(temp_path)

    def test_created_date_invalid_format(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [tag1, tag2, tag3]
created: 10-02-2026
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            # Model C: E003_INVALID_DATE_FORMAT
            assert any("E003_INVALID_DATE_FORMAT" in err and "created" in err for err in errors)
        finally:
            os.unlink(temp_path)

    def test_updated_date_invalid_format(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [tag1, tag2, tag3]
created: 2026-02-10
updated: 10/02/2026
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            # Model C: E003_INVALID_DATE_FORMAT
            assert any("E003_INVALID_DATE_FORMAT" in err and "updated" in err for err in errors)
        finally:
            os.unlink(temp_path)


class TestYAMLParsingErrors:
    """Test YAML parsing edge cases"""

    def test_malformed_yaml(self):
        content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
  indented_incorrectly: value
status: active
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            assert any("YAML parsing error" in err for err in errors)
        finally:
            os.unlink(temp_path)

    def test_empty_yaml_frontmatter(self):
        content = """---\n---\n\n# Content\n"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            assert any("Empty YAML frontmatter" in err for err in errors)
        finally:
            os.unlink(temp_path)

    def test_incomplete_frontmatter(self):
        content = """---
title: "Test File"
type: guide

# Content starts without closing ---
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            assert len(errors) > 0
            # Either structure error or missing fields — both are valid outcomes
            assert any(
                "Invalid YAML frontmatter structure" in err
                or "YAML parsing error" in err
                or "E005_SCHEMA_VIOLATION" in err
                or "E002_MISSING_FIELD" in err
                for err in errors
            )
        finally:
            os.unlink(temp_path)


class TestMultipleFieldErrors:
    """Test files with multiple validation errors"""

    def test_multiple_missing_fields(self):
        content = """---
title: "Test File"
type: guide
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            assert len(errors) >= 5
            # Model C: E002_MISSING_FIELD
            assert any("E002_MISSING_FIELD" in err and "domain" in err for err in errors)
            assert any("E002_MISSING_FIELD" in err and "level" in err for err in errors)
            assert any("E002_MISSING_FIELD" in err and "status" in err for err in errors)
        finally:
            os.unlink(temp_path)

    def test_multiple_invalid_values(self):
        content = """---
title: "Test File"
type: tutorial
domain: Technology
level: expert
status: wip
tags: single-tag
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            errors, warnings = validate_file(temp_path)
            assert len(errors) >= 4
            # Model C: E001 for type/level/status, E006 for domain
            assert any("E001_INVALID_ENUM" in err and "type" in err for err in errors)
            assert any("E001_INVALID_ENUM" in err and "level" in err for err in errors)
            assert any("E001_INVALID_ENUM" in err and "status" in err for err in errors)
            assert any("E006_TAXONOMY_VIOLATION" in err for err in errors)
        finally:
            os.unlink(temp_path)
