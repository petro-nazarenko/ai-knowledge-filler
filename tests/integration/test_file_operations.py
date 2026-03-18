"""Integration tests for file operations

Tests file creation, reading, updating, and deletion operations.
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path


class TestFileCreation:
    """Test creating markdown files"""

    def test_create_markdown_file(self):
        """Test creating a basic markdown file"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        content = """---
title: "Test File"
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

# Content
"""

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            assert os.path.exists(file_path)
            assert os.path.getsize(file_path) > 0

            with open(file_path, "r", encoding="utf-8") as f:
                read_content = f.read()

            assert read_content == content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)

    def test_create_file_in_nested_directory(self):
        """Test creating file in nested directory structure"""
        temp_dir = tempfile.mkdtemp()
        nested_path = os.path.join(temp_dir, "a", "b", "c")

        try:
            os.makedirs(nested_path, exist_ok=True)

            file_path = os.path.join(nested_path, "nested.md")

            with open(file_path, "w") as f:
                f.write("# Test")

            assert os.path.exists(file_path)
            assert Path(file_path).parent == Path(nested_path)

        finally:
            shutil.rmtree(temp_dir)

    def test_create_file_with_special_characters(self):
        """Test creating files with special characters in name"""
        temp_dir = tempfile.mkdtemp()

        # Valid filename with special chars
        file_path = os.path.join(temp_dir, "test-file_v1.0.md")

        try:
            with open(file_path, "w") as f:
                f.write("# Test")

            assert os.path.exists(file_path)

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)

    def test_overwrite_existing_file(self):
        """Test overwriting an existing file"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        try:
            # Create initial file
            with open(file_path, "w") as f:
                f.write("# Original")

            # Overwrite
            with open(file_path, "w") as f:
                f.write("# Updated")

            with open(file_path, "r") as f:
                content = f.read()

            assert content == "# Updated"

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)


class TestFileReading:
    """Test reading markdown files"""

    @pytest.fixture
    def sample_file(self):
        """Create a sample markdown file"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "sample.md")

        content = """---
title: "Sample File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [sample, test]
related:
  - "[[Example]]"
created: 2026-02-10
updated: 2026-02-10
---

# Sample Content

This is a test file.
"""

        with open(file_path, "w") as f:
            f.write(content)

        yield file_path

        # Cleanup
        os.unlink(file_path)
        os.rmdir(temp_dir)

    def test_read_file_content(self, sample_file):
        """Test reading file content"""
        with open(sample_file, "r") as f:
            content = f.read()

        assert content.startswith("---")
        assert "title:" in content
        assert "Sample Content" in content

    def test_read_file_lines(self, sample_file):
        """Test reading file line by line"""
        with open(sample_file, "r") as f:
            lines = f.readlines()

        assert len(lines) > 0
        assert lines[0].strip() == "---"

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            with open("/nonexistent/file.md", "r") as f:
                f.read()


class TestFileUpdating:
    """Test updating markdown files"""

    def test_append_to_file(self):
        """Test appending content to existing file"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        try:
            # Create initial file
            with open(file_path, "w") as f:
                f.write("# Original\n")

            # Append
            with open(file_path, "a") as f:
                f.write("\n## Added Section\n")

            with open(file_path, "r") as f:
                content = f.read()

            assert "# Original" in content
            assert "## Added Section" in content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)

    def test_update_yaml_metadata(self):
        """Test updating YAML frontmatter"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        original_content = """---
title: "Original Title"
type: guide
domain: ai-system
level: intermediate
status: draft
tags: [test]
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""

        try:
            # Create file
            with open(file_path, "w") as f:
                f.write(original_content)

            # Read and update
            with open(file_path, "r") as f:
                content = f.read()

            # Simple replacement (in real scenario use YAML parser)
            updated_content = content.replace("status: draft", "status: active").replace(
                "updated: 2026-02-10", "updated: 2026-02-11"
            )

            with open(file_path, "w") as f:
                f.write(updated_content)

            # Verify
            with open(file_path, "r") as f:
                final_content = f.read()

            assert "status: active" in final_content
            assert "updated: 2026-02-11" in final_content

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rmdir(temp_dir)


class TestFileDeletion:
    """Test deleting markdown files"""

    def test_delete_file(self):
        """Test deleting a file"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.md")

        try:
            # Create file
            with open(file_path, "w") as f:
                f.write("# Test")

            assert os.path.exists(file_path)

            # Delete
            os.unlink(file_path)

            assert not os.path.exists(file_path)

        finally:
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

    def test_delete_directory_with_files(self):
        """Test deleting directory containing files"""
        temp_dir = tempfile.mkdtemp()

        # Create multiple files
        for i in range(3):
            file_path = os.path.join(temp_dir, f"file_{i}.md")
            with open(file_path, "w") as f:
                f.write(f"# File {i}")

        assert len(os.listdir(temp_dir)) == 3

        # Delete directory
        shutil.rmtree(temp_dir)

        assert not os.path.exists(temp_dir)


class TestFilePermissions:
    """Test file permission handling"""

    @pytest.mark.skipif(
        __import__("os").getuid() == 0, reason="read-only chmod has no effect when running as root"
    )
    def test_read_only_file(self):
        """Test handling read-only files"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "readonly.md")

        try:
            # Create file
            with open(file_path, "w") as f:
                f.write("# Read Only")

            # Make read-only
            os.chmod(file_path, 0o444)

            # Try to write (should fail)
            with pytest.raises(PermissionError):
                with open(file_path, "w") as f:
                    f.write("# Modified")

        finally:
            # Restore permissions for cleanup
            if os.path.exists(file_path):
                os.chmod(file_path, 0o644)
                os.unlink(file_path)
            os.rmdir(temp_dir)
