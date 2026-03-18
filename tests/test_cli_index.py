"""Tests for `akf index` CLI subcommand (cli.cmd_index)."""

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is on the path so cli.py is importable directly.
sys.path.insert(0, str(Path(__file__).parent.parent))


def _invoke(args_dict: dict) -> None:
    """Import and invoke cmd_index with a synthetic argparse.Namespace."""
    from cli import cmd_index  # noqa: PLC0415  (lazy import intentional)

    cmd_index(argparse.Namespace(**args_dict))


# ─── Success path ─────────────────────────────────────────────────────────────


class TestCmdIndexSuccess:
    def test_prints_indexed_counts_and_exits_0(self, tmp_path, capsys):
        """cmd_index with a valid corpus dir should print counts and exit 0."""
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        (corpus / "note.md").write_text("# Hello\n\nContent.", encoding="utf-8")

        from rag.config import RAGConfig  # noqa: PLC0415

        cfg = RAGConfig(
            corpus_dir=corpus,
            persist_directory=tmp_path / ".chroma",
            collection_name="akf_corpus",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            markdown_glob="*.md",
            batch_size=64,
        )
        mock_stats = MagicMock(files_indexed=3, chunks_indexed=7)

        with (
            patch("rag.config.load_config", return_value=cfg),
            patch("rag.indexer.index_corpus", return_value=mock_stats),
        ):
            # Should not raise SystemExit
            _invoke({"corpus": None, "reset": False})

        out = capsys.readouterr().out
        assert "3 files" in out
        assert "7 chunks" in out
        assert "akf_corpus" in out


# ─── Missing corpus directory ─────────────────────────────────────────────────


class TestCmdIndexMissingCorpus:
    def test_missing_corpus_dir_exits_1(self, tmp_path, capsys):
        """cmd_index with a non-existent corpus dir must exit with code 1."""
        from rag.config import RAGConfig  # noqa: PLC0415

        cfg = RAGConfig(
            corpus_dir=tmp_path / "no_such_corpus",
            persist_directory=tmp_path / ".chroma",
            collection_name="akf_corpus",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            markdown_glob="*.md",
            batch_size=64,
        )

        with patch("rag.config.load_config", return_value=cfg):
            with pytest.raises(SystemExit) as exc_info:
                _invoke({"corpus": None, "reset": False})

        assert exc_info.value.code == 1
        err_out = capsys.readouterr().out
        assert "not found" in err_out.lower()
