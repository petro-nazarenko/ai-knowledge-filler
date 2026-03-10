"""Canvas generator — builds Obsidian Canvas JSON from validated corpus.

Converts a directory of validated Markdown knowledge files into an Obsidian
Canvas layout where nodes represent files and edges represent relationships
parsed from the ``related`` YAML frontmatter field.
"""

import json
import re
import uuid
from pathlib import Path

import yaml

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

COLUMN_SPACING = 600   # horizontal gap between groups (px)
NODE_SPACING = 300     # vertical gap between nodes within a group (px)
NODE_WIDTH = 300
NODE_HEIGHT = 200

# Obsidian colour strings (1-based index)
DOMAIN_COLORS = {
    "ai-system": "1",
    "system-design": "2",
    "api-design": "3",
    "devops": "4",
    "security": "5",
    "data-engineering": "6",
    "prompt-engineering": "1",
    "backend-engineering": "2",
}

# Regex that matches [[Note Name]] and [[Note Name|rel_type]]
_LINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")


class CanvasGenerator:
    """Generates an Obsidian Canvas JSON file from a corpus of Markdown files.

    Args:
        input_path: Directory containing validated ``.md`` knowledge files.
        output_path: Destination path for the ``.canvas`` JSON file.
        group_by: Frontmatter field used to group nodes into columns.
            Supported values: ``"domain"``, ``"type"``, ``"level"``.
            Defaults to ``"domain"``.

    Example::

        gen = CanvasGenerator()
        canvas = gen.generate(
            "tests/fixtures/corpus/",
            "knowledge.canvas",
            group_by="domain",
        )
    """

    def generate(
        self,
        input_path: str | Path,
        output_path: str | Path,
        group_by: str = "domain",
    ) -> dict:
        """Parse corpus and write an Obsidian Canvas JSON file.

        Args:
            input_path: Path to a directory that contains ``.md`` files.
            output_path: File path where the ``.canvas`` JSON will be written.
            group_by: Frontmatter field to use for column grouping.

        Returns:
            The canvas dictionary that was written to *output_path*.

        Raises:
            ValueError: If *input_path* is not a directory.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.is_dir():
            raise ValueError(f"input_path must be a directory: {input_path}")

        files = self._parse_corpus(input_path)
        nodes = self._build_nodes(files, group_by)
        layout = self._compute_layout(nodes)

        # Apply layout coordinates to nodes and strip internal _group key
        for node in nodes:
            nid = node["id"]
            node["x"], node["y"] = layout[nid]
            node.pop("_group", None)

        edges = self._build_edges(files, nodes)
        canvas = {"nodes": nodes, "edges": edges}

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(canvas, fh, indent=2, ensure_ascii=False)

        return canvas

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _parse_corpus(self, input_path: Path) -> list[dict]:
        """Read all ``.md`` files and extract frontmatter metadata and links.

        Args:
            input_path: Directory containing ``.md`` knowledge files.

        Returns:
            List of file descriptors.  Each descriptor is a ``dict`` with:

            * ``path`` – absolute :class:`~pathlib.Path` to the file.
            * ``rel_path`` – path relative to *input_path* as a POSIX string.
            * ``stem`` – filename without ``.md`` suffix.
            * ``meta`` – ``dict`` of parsed YAML frontmatter (may be empty).
            * ``related`` – list of ``(target_name, label)`` tuples where
              *label* is ``""`` for untyped links.
        """
        files: list[dict] = []
        for md_file in sorted(input_path.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            meta = _extract_frontmatter(content)
            related = _parse_related(meta.get("related") or [])
            files.append(
                {
                    "path": md_file,
                    "rel_path": md_file.relative_to(input_path).as_posix(),
                    "stem": md_file.stem,
                    "meta": meta,
                    "related": related,
                }
            )
        return files

    def _build_nodes(self, files: list[dict], group_by: str) -> list[dict]:
        """Create canvas node objects for every file.

        Args:
            files: Output of :meth:`_parse_corpus`.
            group_by: Frontmatter key used for domain-colour lookup when
                *group_by* is ``"domain"``.

        Returns:
            List of Obsidian Canvas node dicts.  Coordinates are set to
            ``0`` and must be replaced by :meth:`_compute_layout`.
        """
        nodes: list[dict] = []
        for file_info in files:
            domain = file_info["meta"].get("domain", "")
            node: dict = {
                "id": _make_id(file_info["stem"]),
                "type": "file",
                "file": file_info["rel_path"],
                "x": 0,
                "y": 0,
                "width": NODE_WIDTH,
                "height": NODE_HEIGHT,
                "_group": file_info["meta"].get(group_by, ""),
            }
            color = DOMAIN_COLORS.get(domain)
            if color:
                node["color"] = color
            nodes.append(node)
        return nodes

    def _build_edges(self, files: list[dict], nodes: list[dict]) -> list[dict]:
        """Create canvas edge objects from ``related`` link lists.

        Only edges where **both** the source file and the resolved target file
        exist in the corpus are emitted — dangling edges are silently skipped.

        Args:
            files: Output of :meth:`_parse_corpus`.
            nodes: Output of :meth:`_build_nodes` (used for ID lookup).

        Returns:
            List of Obsidian Canvas edge dicts.
        """
        # Build lookup: stem → node id
        stem_to_id: dict[str, str] = {
            file_info["stem"]: node["id"]
            for file_info, node in zip(files, nodes)
        }
        # Build lookup: stem → set for fast existence checks
        stems = set(stem_to_id.keys())

        edges: list[dict] = []
        for file_info, node in zip(files, nodes):
            src_id = node["id"]
            for target_name, label in file_info["related"]:
                target_stem = _resolve_stem(target_name, stems)
                if target_stem is None:
                    continue  # dangling link — skip
                tgt_id = stem_to_id[target_stem]
                edge: dict = {
                    "id": str(uuid.uuid4()),
                    "fromNode": src_id,
                    "toNode": tgt_id,
                    "toEnd": "arrow",
                }
                if label:
                    edge["label"] = label
                edges.append(edge)
        return edges

    def _compute_layout(self, nodes: list[dict]) -> dict[str, tuple[int, int]]:
        """Assign (x, y) pixel coordinates to each node.

        Nodes are arranged in columns, one column per unique value of the
        ``_group`` key embedded by :meth:`_build_nodes`.  Nodes within a
        column are stacked vertically with :data:`NODE_SPACING` pixels between
        them.  Columns are spaced :data:`COLUMN_SPACING` pixels apart.

        Args:
            nodes: List of canvas node dicts, each having ``"id"`` and
                ``"_group"`` keys (set by :meth:`_build_nodes`).

        Returns:
            Mapping from node ``id`` to ``(x, y)`` pixel coordinates.
        """
        groups: dict[str, list[str]] = {}  # group_value → [node_id, ...]
        for node in nodes:
            group_val = node.get("_group", "")
            groups.setdefault(group_val, []).append(node["id"])

        layout: dict[str, tuple[int, int]] = {}
        for col_idx, (_, node_ids) in enumerate(sorted(groups.items())):
            x = col_idx * COLUMN_SPACING
            for row_idx, nid in enumerate(node_ids):
                y = row_idx * NODE_SPACING
                layout[nid] = (x, y)
        return layout


# ─── MODULE-LEVEL HELPERS ─────────────────────────────────────────────────────


def _extract_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter delimited by ``---`` fences.

    Args:
        content: Raw Markdown file content.

    Returns:
        Parsed frontmatter as a ``dict``, or an empty ``dict`` if no valid
        frontmatter block is found or parsing fails.
    """
    match = re.match(r"^---\s*\n(.*?\n)---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    try:
        result = yaml.safe_load(match.group(1))
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError:
        return {}


def _parse_related(related: list) -> list[tuple[str, str]]:
    """Extract ``(target_name, label)`` pairs from the ``related`` list.

    Supports two link formats:

    * Untyped:  ``[[Note Name]]``  → label is ``""``
    * Typed:    ``[[Note Name|rel_type]]``  → label is ``"rel_type"``

    Args:
        related: Raw list of items from the YAML ``related`` field.

    Returns:
        List of ``(target_name, label)`` tuples.  Items that do not contain a
        valid ``[[ … ]]`` link are silently skipped.
    """
    pairs: list[tuple[str, str]] = []
    for item in related:
        if not isinstance(item, str):
            continue
        m = _LINK_RE.search(item)
        if not m:
            continue
        target_name = m.group(1).strip()
        label = (m.group(2) or "").strip()
        pairs.append((target_name, label))
    return pairs


def _resolve_stem(target_name: str, stems: set[str]) -> str | None:
    """Resolve a wiki-link target name to a corpus file stem.

    Tries the following candidates in order:

    1. Exact match (e.g. ``"Note_Name"``).
    2. Spaces replaced by underscores (e.g. ``"Note Name"`` → ``"Note_Name"``).
    3. Underscores replaced by spaces (e.g. ``"Note_Name"`` → ``"Note Name"``).

    Args:
        target_name: The raw text inside ``[[ … ]]``.
        stems: Set of known corpus file stems (without ``.md`` suffix).

    Returns:
        The matching stem, or ``None`` if no candidate matches.
    """
    candidates = [
        target_name,
        target_name.replace(" ", "_"),
        target_name.replace("_", " "),
    ]
    for candidate in candidates:
        if candidate in stems:
            return candidate
    return None


def _make_id(stem: str) -> str:
    """Generate a stable, short node ID from a file stem.

    Uses a deterministic UUID (UUID5, DNS namespace) so the same file always
    gets the same node ID, enabling canvas diffing.

    Args:
        stem: File stem (filename without ``.md`` suffix).

    Returns:
        A 16-character hex string derived from a UUID5 hash.
    """
    return uuid.uuid5(uuid.NAMESPACE_DNS, stem).hex[:16]
