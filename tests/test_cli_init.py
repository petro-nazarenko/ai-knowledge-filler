"""tests/test_cli_init.py — Tests for akf init command"""
from __future__ import annotations
from pathlib import Path
import pytest
from cli import cmd_init

class Args:
    def __init__(self, path=None, force=False):
        self.path = path
        self.force = force

class TestCmdInit:
    def test_creates_akf_yaml_in_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cmd_init(Args())
        assert (tmp_path / "akf.yaml").exists()

    def test_creates_in_specified_path(self, tmp_path):
        cmd_init(Args(path=str(tmp_path)))
        assert (tmp_path / "akf.yaml").exists()

    def test_creates_dir_if_missing(self, tmp_path):
        target = tmp_path / "new" / "vault"
        cmd_init(Args(path=str(target)))
        assert (target / "akf.yaml").exists()

    def test_created_file_is_valid_yaml(self, tmp_path):
        import yaml
        cmd_init(Args(path=str(tmp_path)))
        content = yaml.safe_load((tmp_path / "akf.yaml").read_text())
        assert "taxonomy" in content
        assert "enums" in content

    def test_aborts_if_exists_without_force(self, tmp_path):
        (tmp_path / "akf.yaml").write_text("original\n")
        with pytest.raises(SystemExit) as exc:
            cmd_init(Args(path=str(tmp_path)))
        assert exc.value.code == 1
        assert (tmp_path / "akf.yaml").read_text() == "original\n"

    def test_force_overwrites(self, tmp_path):
        (tmp_path / "akf.yaml").write_text("original\n")
        cmd_init(Args(path=str(tmp_path), force=True))
        assert "taxonomy" in (tmp_path / "akf.yaml").read_text()


def test_init_force_creates_backup(tmp_path):
    """SEC-L2: --force must create .bak before overwrite."""
    from unittest.mock import patch, MagicMock
    import shutil
    from pathlib import Path

    # Create existing akf.yaml
    existing = tmp_path / "akf.yaml"
    existing.write_text("original content")

    args = MagicMock()
    args.path = str(tmp_path)
    args.force = True

    with patch("cli.Path") as mock_path, \
         patch("shutil.copy") as mock_copy, \
         patch("akf.__file__", str(tmp_path / "akf/__init__.py")):
        pass  # Use real implementation

    # Real test via CLI directly
    import sys, importlib
    cli = importlib.import_module("cli")

    args2 = MagicMock()
    args2.path = str(tmp_path)
    args2.force = True

    try:
        cli.cmd_init(args2)
    except SystemExit:
        pass

    backup = tmp_path / "akf.yaml.bak"
    assert backup.exists(), "Backup file must be created on --force"
    assert backup.read_text() == "original content"
