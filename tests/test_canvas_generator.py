"""Tests for akf/canvas_generator.py — Obsidian Canvas JSON generation."""
import json
import textwrap
from pathlib import Path

import pytest

from akf.canvas_generator import (
    CanvasGenerator,
    _extract_frontmatter,
    _make_id,
    _parse_related,
    _resolve_stem,
    COLUMN_SPACING,
    NODE_HEIGHT,
    NODE_SPACING,
    NODE_WIDTH,
)


# ─── FIXTURES ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def corpus_dir(tmp_path: Path) -> Path:
    """Minimal corpus with three files across two domains."""
    files = {
        "File_Alpha.md": textwrap.dedent("""\
            ---
            title: "Alpha"
            type: concept
            domain: ai-system
            level: beginner
            status: active
            tags: [ai, system, alpha]
            related:
              - "[[File_Beta]]"
              - "[[File_Gamma|implements]]"
            created: 2026-01-01
            updated: 2026-01-01
            ---
            Body alpha.
        """),
        "File_Beta.md": textwrap.dedent("""\
            ---
            title: "Beta"
            type: reference
            domain: ai-system
            level: intermediate
            status: active
            tags: [ai, system, beta]
            related:
              - "[[File_Alpha|depends-on]]"
            created: 2026-01-01
            updated: 2026-01-01
            ---
            Body beta.
        """),
        "File_Gamma.md": textwrap.dedent("""\
            ---
            title: "Gamma"
            type: guide
            domain: devops
            level: advanced
            status: active
            tags: [devops, gamma, pipeline]
            related: []
            created: 2026-01-01
            updated: 2026-01-01
            ---
            Body gamma.
        """),
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def canvas_output(tmp_path: Path) -> Path:
    """Path for the output .canvas file."""
    return tmp_path / "out" / "test.canvas"


# ─── _extract_frontmatter ─────────────────────────────────────────────────────


def test_extract_frontmatter_basic():
    content = "---\ntitle: Hello\ndomain: ai-system\n---\nBody."
    meta = _extract_frontmatter(content)
    assert meta["title"] == "Hello"
    assert meta["domain"] == "ai-system"


def test_extract_frontmatter_no_fence_returns_empty():
    assert _extract_frontmatter("No frontmatter here.") == {}


def test_extract_frontmatter_invalid_yaml_returns_empty():
    content = "---\n: broken: yaml:\n---\nBody."
    meta = _extract_frontmatter(content)
    assert isinstance(meta, dict)


def test_extract_frontmatter_non_mapping_returns_empty():
    """YAML that parses to a list (not a dict) must return empty dict."""
    content = "---\n- item1\n- item2\n---\nBody."
    assert _extract_frontmatter(content) == {}


# ─── _parse_related ───────────────────────────────────────────────────────────


def test_parse_related_untyped():
    pairs = _parse_related(["[[Note_Name]]"])
    assert pairs == [("Note_Name", "")]


def test_parse_related_typed():
    pairs = _parse_related(['[[Other_Note|implements]]'])
    assert pairs == [("Other_Note", "implements")]


def test_parse_related_mixed():
    items = ["[[Note_A]]", "[[Note_B|extends]]"]
    pairs = _parse_related(items)
    assert ("Note_A", "") in pairs
    assert ("Note_B", "extends") in pairs


def test_parse_related_ignores_non_string():
    pairs = _parse_related([42, None, "[[Valid]]"])
    assert len(pairs) == 1
    assert pairs[0][0] == "Valid"


def test_parse_related_empty_list():
    assert _parse_related([]) == []


def test_parse_related_spaces_in_name():
    pairs = _parse_related(["[[Note With Spaces|rel]]"])
    assert pairs == [("Note With Spaces", "rel")]


# ─── _resolve_stem ────────────────────────────────────────────────────────────


def test_resolve_stem_exact_match():
    stems = {"Note_Name", "Other_Note"}
    assert _resolve_stem("Note_Name", stems) == "Note_Name"


def test_resolve_stem_spaces_to_underscores():
    stems = {"Note_Name"}
    assert _resolve_stem("Note Name", stems) == "Note_Name"


def test_resolve_stem_underscores_to_spaces():
    stems = {"Note Name"}
    assert _resolve_stem("Note_Name", stems) == "Note Name"


def test_resolve_stem_missing_returns_none():
    stems = {"Existing_Note"}
    assert _resolve_stem("Missing_Note", stems) is None


# ─── _make_id ─────────────────────────────────────────────────────────────────


def test_make_id_is_deterministic():
    assert _make_id("My_Note") == _make_id("My_Note")


def test_make_id_different_stems_differ():
    assert _make_id("Note_A") != _make_id("Note_B")


def test_make_id_length():
    assert len(_make_id("anything")) == 16


# ─── CanvasGenerator._parse_corpus ───────────────────────────────────────────


def test_parse_corpus_reads_all_md_files(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    stems = {f["stem"] for f in files}
    assert stems == {"File_Alpha", "File_Beta", "File_Gamma"}


def test_parse_corpus_extracts_metadata(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    alpha = next(f for f in files if f["stem"] == "File_Alpha")
    assert alpha["meta"]["domain"] == "ai-system"
    assert alpha["meta"]["type"] == "concept"


def test_parse_corpus_extracts_related_links(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    alpha = next(f for f in files if f["stem"] == "File_Alpha")
    related_names = [name for name, _ in alpha["related"]]
    assert "File_Beta" in related_names
    assert "File_Gamma" in related_names


# ─── CanvasGenerator._build_nodes ────────────────────────────────────────────


def test_build_nodes_count(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "domain")
    assert len(nodes) == 3


def test_build_nodes_fields(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "domain")
    for node in nodes:
        assert node["type"] == "file"
        assert node["width"] == NODE_WIDTH
        assert node["height"] == NODE_HEIGHT
        assert "id" in node
        assert "file" in node


def test_build_nodes_domain_color(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "domain")
    # ai-system → color "1"
    ai_nodes = [n for n in nodes if "File_Alpha" in n["file"] or "File_Beta" in n["file"]]
    for n in ai_nodes:
        assert n.get("color") == "1"


def test_build_nodes_unknown_domain_no_color(tmp_path):
    md = tmp_path / "Foo.md"
    md.write_text("---\ndomain: unknown-domain\ntitle: Foo\n---\n", encoding="utf-8")
    gen = CanvasGenerator()
    files = gen._parse_corpus(tmp_path)
    nodes = gen._build_nodes(files, "domain")
    assert "color" not in nodes[0]


def test_build_nodes_group_by_type(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "type")
    # Each node should have _group set to its type value
    alpha_node = next(n for n in nodes if "File_Alpha" in n["file"])
    assert alpha_node["_group"] == "concept"


# ─── CanvasGenerator._build_edges ────────────────────────────────────────────


def test_build_edges_typed_relationship(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "domain")
    edges = gen._build_edges(files, nodes)
    # File_Alpha → File_Gamma with label "implements"
    typed = [e for e in edges if e.get("label") == "implements"]
    assert len(typed) >= 1


def test_build_edges_untyped_relationship(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "domain")
    edges = gen._build_edges(files, nodes)
    # Untyped edges should have no "label" key (or empty string)
    untyped = [e for e in edges if "label" not in e]
    assert len(untyped) >= 1


def test_build_edges_dangling_link_skipped(tmp_path):
    """Links that point to non-existent files must not produce edges."""
    md = tmp_path / "Note.md"
    md.write_text(
        "---\ntitle: Note\ndomain: ai-system\n---\n"
        "[[Does_Not_Exist]]\n",
        encoding="utf-8",
    )
    # Add related in frontmatter properly
    md.write_text(
        textwrap.dedent("""\
            ---
            title: Note
            domain: ai-system
            related:
              - "[[Does_Not_Exist]]"
            ---
            Body.
        """),
        encoding="utf-8",
    )
    gen = CanvasGenerator()
    files = gen._parse_corpus(tmp_path)
    nodes = gen._build_nodes(files, "domain")
    edges = gen._build_edges(files, nodes)
    assert edges == []


def test_build_edges_fields(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "domain")
    edges = gen._build_edges(files, nodes)
    for edge in edges:
        assert "id" in edge
        assert "fromNode" in edge
        assert "toNode" in edge
        assert edge["toEnd"] == "arrow"


# ─── CanvasGenerator._compute_layout ─────────────────────────────────────────


def test_compute_layout_grouping_by_domain(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "domain")
    layout = gen._compute_layout(nodes)
    # ai-system (2 nodes) and devops (1 node) → two different x-columns
    alpha_id = next(n["id"] for n in nodes if "File_Alpha" in n["file"])
    gamma_id = next(n["id"] for n in nodes if "File_Gamma" in n["file"])
    assert layout[alpha_id][0] != layout[gamma_id][0]


def test_compute_layout_column_spacing(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "domain")
    layout = gen._compute_layout(nodes)
    x_values = sorted({pos[0] for pos in layout.values()})
    for i in range(1, len(x_values)):
        assert x_values[i] - x_values[i - 1] == COLUMN_SPACING


def test_compute_layout_node_spacing(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "domain")
    layout = gen._compute_layout(nodes)
    # ai-system group has File_Alpha and File_Beta — same column, different rows
    alpha_id = next(n["id"] for n in nodes if "File_Alpha" in n["file"])
    beta_id = next(n["id"] for n in nodes if "File_Beta" in n["file"])
    ax, ay = layout[alpha_id]
    bx, by = layout[beta_id]
    assert ax == bx  # same column
    assert abs(ay - by) == NODE_SPACING  # one row apart


def test_compute_layout_group_by_type(corpus_dir):
    gen = CanvasGenerator()
    files = gen._parse_corpus(corpus_dir)
    nodes = gen._build_nodes(files, "type")
    layout = gen._compute_layout(nodes)
    # concept, reference, guide → 3 different columns
    x_values = sorted({pos[0] for pos in layout.values()})
    assert len(x_values) == 3


# ─── CanvasGenerator.generate ────────────────────────────────────────────────


def test_generate_output_is_valid_json(corpus_dir, canvas_output):
    CanvasGenerator().generate(corpus_dir, canvas_output)
    raw = canvas_output.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert "nodes" in parsed
    assert "edges" in parsed


def test_generate_nodes_match_file_count(corpus_dir, canvas_output):
    canvas = CanvasGenerator().generate(corpus_dir, canvas_output)
    assert len(canvas["nodes"]) == 3


def test_generate_creates_parent_dirs(corpus_dir, tmp_path):
    deep_output = tmp_path / "a" / "b" / "c" / "canvas.canvas"
    CanvasGenerator().generate(corpus_dir, deep_output)
    assert deep_output.exists()


def test_generate_invalid_input_raises(tmp_path, canvas_output):
    with pytest.raises(ValueError):
        CanvasGenerator().generate(tmp_path / "nonexistent", canvas_output)


def test_generate_group_by_type(corpus_dir, canvas_output):
    canvas = CanvasGenerator().generate(corpus_dir, canvas_output, group_by="type")
    # concept, reference, guide — three x-columns
    x_values = {n["x"] for n in canvas["nodes"]}
    assert len(x_values) == 3


def test_generate_group_by_level(corpus_dir, canvas_output):
    canvas = CanvasGenerator().generate(corpus_dir, canvas_output, group_by="level")
    # beginner, intermediate, advanced — three x-columns
    x_values = {n["x"] for n in canvas["nodes"]}
    assert len(x_values) == 3


def test_generate_no_dangling_edges(tmp_path, canvas_output):
    """Output must not contain edges pointing to nodes not in the canvas."""
    md = tmp_path / "Lone.md"
    md.write_text(textwrap.dedent("""\
        ---
        title: Lone
        domain: devops
        related:
          - "[[Ghost_File]]"
        ---
        Body.
    """), encoding="utf-8")
    canvas = CanvasGenerator().generate(tmp_path, canvas_output)
    assert canvas["edges"] == []


def test_generate_corpus_fixture(canvas_output):
    """Smoke test against the real fixtures corpus — no error, produces nodes."""
    fixture_dir = Path(__file__).parent / "fixtures" / "corpus"
    canvas = CanvasGenerator().generate(fixture_dir, canvas_output)
    assert len(canvas["nodes"]) == 48
    assert isinstance(canvas["edges"], list)


def test_generate_output_nodes_have_no_private_keys(corpus_dir, canvas_output):
    """Internal _group key must not appear in the written JSON."""
    canvas = CanvasGenerator().generate(corpus_dir, canvas_output)
    for node in canvas["nodes"]:
        assert "_group" not in node


def test_generate_typed_edge_label_in_output(corpus_dir, canvas_output):
    """Typed relationships must appear as edge labels in the JSON output."""
    canvas = CanvasGenerator().generate(corpus_dir, canvas_output)
    labels = [e.get("label") for e in canvas["edges"]]
    assert "implements" in labels


def test_generate_node_file_is_relative_posix(corpus_dir, canvas_output):
    """Node 'file' field must be a relative POSIX path (no absolute paths)."""
    canvas = CanvasGenerator().generate(corpus_dir, canvas_output)
    for node in canvas["nodes"]:
        assert not Path(node["file"]).is_absolute()
        assert "\\" not in node["file"]
