"""Integration tests for validate_yaml CLI functionality"""

import pytest
import tempfile
import os
import shutil
from Scripts.validate_yaml import main


class TestCLIIntegration:
    """Test main() function with real file structures"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory with markdown files"""
        temp_dir = tempfile.mkdtemp()

        # Create valid file
        valid_content = """---
title: "Valid File"
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
        with open(os.path.join(temp_dir, "valid.md"), "w") as f:
            f.write(valid_content)

        # Create invalid file
        invalid_content = """---
title: "Invalid File"
type: invalid-type
---

# Content
"""
        with open(os.path.join(temp_dir, "invalid.md"), "w") as f:
            f.write(invalid_content)

        # Create file with warnings
        warning_content = """---
title: "Warning File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [tag1]
created: 2026-02-10
updated: 2026-02-10
---

# Content
"""
        with open(os.path.join(temp_dir, "warning.md"), "w") as f:
            f.write(warning_content)

        # Create non-markdown file (should be ignored)
        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write("# README\nThis should be ignored")

        # Create subdirectory with file
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "nested.md"), "w") as f:
            f.write(valid_content)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_main_all_valid_files(self, capsys):
        """Test main() with all valid files"""
        valid_dir = tempfile.mkdtemp()

        valid_content = """---
title: "Valid File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [tag1, tag2, tag3]
created: 2026-02-10
updated: 2026-02-10
related:
  - "[[Example Link]]"
---

# Content
"""
        with open(os.path.join(valid_dir, "valid1.md"), "w") as f:
            f.write(valid_content)
        with open(os.path.join(valid_dir, "valid2.md"), "w") as f:
            f.write(valid_content)

        original_dir = os.getcwd()
        os.chdir(valid_dir)

        try:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "✅ All files valid!" in captured.out
            assert "Valid: 2" in captured.out

        finally:
            os.chdir(original_dir)
            shutil.rmtree(valid_dir)

    def test_main_with_errors(self, temp_project_dir, capsys):
        """Test main() exits with code 1 when errors found"""
        original_dir = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            captured = capsys.readouterr()
            assert "❌ Validation failed" in captured.out

        finally:
            os.chdir(original_dir)

    def test_main_counts_files_correctly(self, temp_project_dir, capsys):
        """Test main() counts files correctly"""
        original_dir = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            with pytest.raises(SystemExit):
                main()

            captured = capsys.readouterr()
            assert "Total files: 4" in captured.out

        finally:
            os.chdir(original_dir)

    def test_main_output_formatting(self, temp_project_dir, capsys):
        """Test main() produces properly formatted output"""
        original_dir = os.getcwd()
        os.chdir(temp_project_dir)

        try:
            with pytest.raises(SystemExit):
                main()

            captured = capsys.readouterr()
            assert "🔍 AI Knowledge Filler" in captured.out
            assert "📊 Validation Summary:" in captured.out

        finally:
            os.chdir(original_dir)

    def test_main_handles_no_markdown_files(self, capsys):
        """Test main() with directory containing no markdown files"""
        empty_dir = tempfile.mkdtemp()

        with open(os.path.join(empty_dir, "README.txt"), "w") as f:
            f.write("Text file")

        original_dir = os.getcwd()
        os.chdir(empty_dir)

        try:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "Total files: 0" in captured.out

        finally:
            os.chdir(original_dir)
            shutil.rmtree(empty_dir)


class TestCLIEdgeCases:
    """Test edge cases in CLI execution"""

    def test_main_with_recursive_subdirectories(self):
        """Test main() validates files in nested subdirectories"""
        temp_dir = tempfile.mkdtemp()

        nested_path = os.path.join(temp_dir, "a", "b", "c")
        os.makedirs(nested_path)

        valid_content = """---
title: "Nested File"
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
        with open(os.path.join(nested_path, "nested.md"), "w") as f:
            f.write(valid_content)

        original_dir = os.getcwd()
        os.chdir(temp_dir)

        try:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        finally:
            os.chdir(original_dir)
            shutil.rmtree(temp_dir)


def test_sanitize_filename_blocks_path_traversal(tmp_path):
    """SEC-M2: sanitize_filename must reject path traversal attempts."""
    from cli import sanitize_filename

    # Normal filename — must pass
    result = sanitize_filename("guide_docker.md", tmp_path)
    assert result == tmp_path / "guide_docker.md"

    # Path traversal — Path.name strips directory components, stays inside output_dir
    for malicious in ["../../etc/passwd", "../secret.md", "/abs/path.md"]:
        result = sanitize_filename(malicious, tmp_path)
        assert result.parent == tmp_path
