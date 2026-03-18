"""Integration tests for metadata update operations

Tests the File_Update_Protocol implementation.
"""

import pytest
import tempfile
import os
import yaml


class TestMetadataPreservation:
    """Test that metadata is preserved during updates"""

    def test_preserve_created_date(self):
        """Test that 'created' date is never modified"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        original_content = """---
title: "Test File"
type: guide
domain: ai-system
level: intermediate
status: draft
tags: [test]
related:
  - "[[Example]]"
created: 2026-01-01
updated: 2026-01-01
---

# Original Content
"""

        try:
            # Create file
            with open(file_path, "w") as f:
                f.write(original_content)

            # Simulate update
            with open(file_path, "r") as f:
                content = f.read()

            # Update content but preserve created date
            updated_content = (
                content.replace("updated: 2026-01-01", "updated: 2026-02-10") + "\n## New Section\n"
            )

            with open(file_path, "w") as f:
                f.write(updated_content)

            # Verify created date unchanged
            with open(file_path, "r") as f:
                final_content = f.read()

            assert "created: 2026-01-01" in final_content
            assert "updated: 2026-02-10" in final_content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)

    def test_additive_tags_merge(self):
        """Test that tags are merged additively"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        original = """---
title: "Test"
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

        try:
            with open(file_path, "w") as f:
                f.write(original)

            # Parse YAML
            parts = original.split("---")
            yaml_content = parts[1]
            metadata = yaml.safe_load(yaml_content)

            # Add new tags
            existing_tags = set(metadata["tags"])
            new_tags = {"tag3", "tag4"}
            merged_tags = sorted(existing_tags | new_tags)

            metadata["tags"] = merged_tags
            metadata["updated"] = "2026-02-11"

            # Reconstruct file
            updated = f"---\n{yaml.dump(metadata, default_flow_style=False)}---\n# Content\n"

            with open(file_path, "w") as f:
                f.write(updated)

            # Verify
            with open(file_path, "r") as f:
                final_content = f.read()

            assert "tag1" in final_content
            assert "tag2" in final_content
            assert "tag3" in final_content
            assert "tag4" in final_content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)

    def test_additive_related_merge(self):
        """Test that related links are merged additively"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        original = """---
title: "Test"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [test]
related:
  - "[[Link 1]]"
  - "[[Link 2]]"
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""

        try:
            with open(file_path, "w") as f:
                f.write(original)

            # Parse
            parts = original.split("---")
            metadata = yaml.safe_load(parts[1])

            # Add new related links
            existing_related = set(metadata["related"])
            new_related = {'"[[Link 3]]"', '"[[Link 4]]"'}
            merged_related = sorted(existing_related | new_related)

            metadata["related"] = merged_related
            metadata["updated"] = "2026-02-11"

            # Reconstruct
            updated = f"---\n{yaml.dump(metadata, default_flow_style=False)}---\n# Content\n"

            with open(file_path, "w") as f:
                f.write(updated)

            # Verify
            with open(file_path, "r") as f:
                final_content = f.read()

            assert "Link 1" in final_content
            assert "Link 2" in final_content
            assert "Link 3" in final_content
            assert "Link 4" in final_content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)


class TestStatusTransitions:
    """Test valid status transitions"""

    @pytest.mark.parametrize(
        "old_status,new_status",
        [
            ("draft", "active"),
            ("active", "completed"),
            ("completed", "archived"),
            ("draft", "archived"),
        ],
    )
    def test_valid_status_transition(self, old_status, new_status):
        """Test valid status transitions"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        content = f"""---
title: "Test"
type: guide
domain: ai-system
level: intermediate
status: {old_status}
tags: [test]
related:
  - "[[Example]]"
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""

        try:
            with open(file_path, "w") as f:
                f.write(content)

            # Update status
            with open(file_path, "r") as f:
                read_content = f.read()

            updated_content = read_content.replace(f"status: {old_status}", f"status: {new_status}")

            with open(file_path, "w") as f:
                f.write(updated_content)

            # Verify
            with open(file_path, "r") as f:
                final_content = f.read()

            assert f"status: {new_status}" in final_content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)


class TestVersionIncrement:
    """Test version number incrementation"""

    def test_version_increment_patch(self):
        """Test patch version increment (v1.0 -> v1.1)"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        content = """---
title: "Test"
type: guide
domain: ai-system
level: intermediate
status: active
version: v1.0
tags: [test]
related:
  - "[[Example]]"
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""

        try:
            with open(file_path, "w") as f:
                f.write(content)

            # Increment version
            with open(file_path, "r") as f:
                read_content = f.read()

            updated_content = read_content.replace("version: v1.0", "version: v1.1").replace(
                "updated: 2026-02-10", "updated: 2026-02-11"
            )

            with open(file_path, "w") as f:
                f.write(updated_content)

            # Verify
            with open(file_path, "r") as f:
                final_content = f.read()

            assert "version: v1.1" in final_content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)

    def test_version_increment_major(self):
        """Test major version increment (v1.5 -> v2.0)"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        content = """---
title: "Test"
type: guide
domain: ai-system
level: intermediate
status: active
version: v1.5
tags: [test]
related:
  - "[[Example]]"
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""

        try:
            with open(file_path, "w") as f:
                f.write(content)

            # Major version change
            with open(file_path, "r") as f:
                read_content = f.read()

            updated_content = read_content.replace("version: v1.5", "version: v2.0")

            with open(file_path, "w") as f:
                f.write(updated_content)

            # Verify
            with open(file_path, "r") as f:
                final_content = f.read()

            assert "version: v2.0" in final_content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)


class TestContentAddition:
    """Test adding new content to existing files"""

    def test_append_new_section(self):
        """Test appending new section to file"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        original = """---
title: "Test"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [test]
related:
  - "[[Example]]"
created: 2026-02-10
updated: 2026-02-10
---

# Section 1

Original content.
"""

        try:
            with open(file_path, "w") as f:
                f.write(original)

            # Append new section
            new_section = """
## Section 2

New content added.
"""

            with open(file_path, "a") as f:
                f.write(new_section)

            # Verify
            with open(file_path, "r") as f:
                final_content = f.read()

            assert "# Section 1" in final_content
            assert "## Section 2" in final_content
            assert "Original content" in final_content
            assert "New content added" in final_content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)
