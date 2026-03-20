"""Utilities for extracting pipeline lineage graphs from SQL steps."""

from __future__ import annotations

import os
import re
import struct
import zlib
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError


CREATE_PATTERN = re.compile(r"create\s+table\s+(\w+)", re.IGNORECASE)
INSERT_PATTERN = re.compile(r"insert\s+into\s+(\w+)", re.IGNORECASE)
FROM_PATTERN = re.compile(r"from\s+(\w+)", re.IGNORECASE)
JOIN_PATTERN = re.compile(r"join\s+(\w+)", re.IGNORECASE)


def extract_lineage(steps: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Build lineage edges (source -> target) from SQL pipeline steps."""

    ordered_edges: list[tuple[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()

    for step in steps:
        metadata = extract_step_metadata(step)
        target = metadata.get("target")
        if not isinstance(target, str) or not target:
            continue

        sources = metadata.get("sources", [])
        if not isinstance(sources, list):
            continue

        for source in sources:
            edge = (source, target)
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            ordered_edges.append(edge)

    return ordered_edges


def extract_step_metadata(step: dict[str, Any]) -> dict[str, Any]:
    """Return the target and source tables for a single pipeline step."""

    query = step.get("query", "")
    if not isinstance(query, str) or not query.strip():
        return {"target": None, "sources": [], "query": ""}

    try:
        parsed = parse_one(query)
    except ParseError:
        return _fallback_step_metadata(query)

    return _extract_metadata_from_expression(parsed, query)


def format_lineage_graph(edges: list[tuple[str, str]]) -> str:
    """Render lineage edges into a readable pipeline graph."""

    if not edges:
        return "No source-target lineage relationships were detected."

    lines = []
    lines.append("PIPELINE DATA LINEAGE")
    lines.append("---------------------")

    for source, target in edges:
        lines.append(f"{source} -> {target}")

    return "\n".join(lines)


def generate_pipeline_graph(
    lineage: list[tuple[str, str]],
    output_path: str = "output/pipeline_graph.png",
) -> str:
    """Generate a pipeline graph and save it as PNG, SVG, or DOT."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    file_format = output.suffix.lstrip(".").lower() or "png"

    nodes = {node for edge in lineage for node in edge}
    dot_lines = [
        "digraph pipeline_lineage {",
        "  rankdir=LR;",
        '  node [shape=box style="rounded,filled" fillcolor="lightgoldenrod1"];',
        '  edge [color="steelblue4"];',
    ]
    for node in sorted(nodes):
        dot_lines.append(f'  "{node}";')
    for source, target in lineage:
        dot_lines.append(f'  "{source}" -> "{target}";')
    dot_lines.append("}")
    dot_source = "\n".join(dot_lines)

    if not lineage:
        dot_path = output.with_suffix(".dot")
        dot_path.write_text(dot_source, encoding="utf-8")
        return str(dot_path)

    _ensure_graphviz_on_path()

    try:
        from graphviz import Digraph
    except ImportError:
        if file_format == "png":
            _render_png_fallback(lineage, output)
            return str(output)
        dot_path = output.with_suffix(".dot")
        dot_path.write_text(dot_source, encoding="utf-8")
        return str(dot_path)

    if file_format not in {"png", "svg"}:
        raise ValueError("Only PNG and SVG outputs are supported.")

    render_path = output.with_suffix("")
    graph = Digraph(name="pipeline_lineage", format=file_format)
    graph.attr(rankdir="LR")
    graph.attr("node", shape="box", style="rounded,filled", fillcolor="lightgoldenrod1")
    graph.attr("edge", color="steelblue4")

    for node in sorted(nodes):
        graph.node(node, node)

    for source, target in lineage:
        graph.edge(source, target)

    try:
        rendered_file = graph.render(str(render_path), cleanup=True)
        return str(Path(rendered_file))
    except Exception:
        if file_format == "png":
            _render_png_fallback(lineage, output)
            return str(output)
        dot_path = output.with_suffix(".dot")
        dot_path.write_text(dot_source, encoding="utf-8")
        return str(dot_path)


def _extract_metadata_from_expression(
    parsed: exp.Expression,
    query: str,
) -> dict[str, Any]:
    """Return target and source metadata from a parsed SQL expression."""

    target = _extract_target(parsed)
    source_expression = _extract_source_expression(parsed)
    if source_expression is None:
        return {"target": target, "sources": [], "query": query}

    cte_sources = _build_cte_sources(source_expression)
    sources = _collect_sources(source_expression, cte_sources)
    return {
        "target": target,
        "sources": sources,
        "query": query,
    }


def _extract_target(parsed: exp.Expression) -> str | None:
    """Return the produced target table for a SQL statement."""

    if isinstance(parsed, exp.Create):
        return _table_name_from_expression(parsed.this)

    if isinstance(parsed, exp.Insert):
        return _table_name_from_expression(parsed.this)

    return None


def _extract_source_expression(parsed: exp.Expression) -> exp.Expression | None:
    """Return the expression that provides upstream source tables."""

    if isinstance(parsed, exp.Create):
        expression = parsed.expression
        return expression if isinstance(expression, exp.Expression) else None

    if isinstance(parsed, exp.Insert):
        expression = parsed.expression
        return expression if isinstance(expression, exp.Expression) else None

    if isinstance(parsed, exp.Select):
        return parsed

    if isinstance(parsed, exp.With):
        return parsed

    return parsed if isinstance(parsed, exp.Expression) else None


def _build_cte_sources(expression: exp.Expression) -> dict[str, list[str]]:
    """Return a mapping of CTE name to its resolved upstream sources."""

    cte_sources: dict[str, list[str]] = {}
    with_expression = expression.args.get("with_") or expression.args.get("with")
    if not isinstance(with_expression, exp.With):
        return cte_sources

    for cte in with_expression.expressions:
        if not isinstance(cte, exp.CTE):
            continue

        cte_name = _normalize_name(cte.alias_or_name)
        if not cte_name:
            continue

        cte_sources[cte_name] = _collect_sources(
            cte.this,
            cte_sources,
            include_cte_definition_tables=True,
        )

    return cte_sources


def _collect_sources(
    expression: exp.Expression,
    cte_sources: dict[str, list[str]],
    include_cte_definition_tables: bool = False,
) -> list[str]:
    """Collect upstream source tables, expanding aliases and CTE references."""

    sources: list[str] = []
    seen_sources: set[str] = set()

    for table in expression.find_all(exp.Table):
        if not include_cte_definition_tables and _is_within_cte_definition(table):
            continue

        table_name = _normalize_name(table.name)
        if not table_name:
            continue

        expanded_sources = cte_sources.get(table_name, [table_name])
        for source in expanded_sources:
            if source in seen_sources:
                continue
            seen_sources.add(source)
            sources.append(source)

    return sources


def _is_within_cte_definition(node: exp.Expression) -> bool:
    """Return whether the node belongs to a CTE definition body."""

    parent = node.parent
    while parent is not None:
        if isinstance(parent, exp.CTE):
            return True
        parent = parent.parent

    return False


def _table_name_from_expression(expression: Any) -> str | None:
    """Return a normalized table name from a SQLGlot expression."""

    if isinstance(expression, exp.Table):
        return _normalize_name(expression.name)

    if isinstance(expression, exp.Schema):
        return _table_name_from_expression(expression.this)

    if isinstance(expression, exp.Identifier):
        return _normalize_name(expression.name)

    return None


def _normalize_name(name: Any) -> str:
    """Return a lowercase normalized SQL identifier."""

    if not isinstance(name, str):
        return ""

    return name.strip().strip('"').strip("`").strip("[]").lower()


def _fallback_step_metadata(query: str) -> dict[str, Any]:
    """Return best-effort lineage metadata using regexes."""

    normalized_query = query.lower()
    create_match = CREATE_PATTERN.search(normalized_query)
    insert_match = INSERT_PATTERN.search(normalized_query)

    target = None
    if create_match:
        target = create_match.group(1)
    elif insert_match:
        target = insert_match.group(1)

    sources = FROM_PATTERN.findall(normalized_query)
    sources += JOIN_PATTERN.findall(normalized_query)

    ordered_sources: list[str] = []
    seen_sources: set[str] = set()
    for source in sources:
        if source in seen_sources:
            continue
        seen_sources.add(source)
        ordered_sources.append(source)

    return {"target": target, "sources": ordered_sources, "query": query}


def _ensure_graphviz_on_path() -> None:
    """Add common Graphviz install locations to PATH when available."""

    candidate_paths: list[str] = []

    graphviz_dot = os.getenv("GRAPHVIZ_DOT")
    if graphviz_dot:
        candidate_paths.append(str(Path(graphviz_dot).parent))

    graphviz_bin = os.getenv("GRAPHVIZ_BIN")
    if graphviz_bin:
        candidate_paths.append(graphviz_bin)

    candidate_paths.extend(
        [
            r"C:\Program Files\Graphviz\bin",
            r"C:\Program Files (x86)\Graphviz\bin",
            str(Path.home() / "AppData" / "Local" / "Programs" / "Graphviz" / "bin"),
            r"C:\ProgramData\chocolatey\bin",
            str(Path.home() / "scoop" / "apps" / "graphviz" / "current" / "bin"),
        ]
    )

    existing_paths = os.environ.get("PATH", "").split(os.pathsep)
    for candidate in candidate_paths:
        if not candidate:
            continue
        dot_candidate = Path(candidate) / "dot.exe"
        if not dot_candidate.exists():
            continue
        if candidate in existing_paths:
            return
        os.environ["PATH"] = os.pathsep.join([candidate, *existing_paths])
        return


def _render_png_fallback(lineage: list[tuple[str, str]], output: Path) -> None:
    """Render a simple PNG lineage graph without Graphviz system binaries."""

    nodes = _ordered_nodes(lineage)
    if not nodes:
        _write_png(output, 240, 120, bytes([255, 255, 255] * 240 * 120))
        return

    levels = _assign_levels(lineage, nodes)
    rows_by_level: dict[int, list[str]] = defaultdict(list)
    for node in nodes:
        rows_by_level[levels[node]].append(node)

    margin_x = 40
    margin_y = 40
    box_width = 180
    box_height = 44
    horizontal_gap = 80
    vertical_gap = 36

    max_level = max(levels.values(), default=0)
    max_rows = max((len(items) for items in rows_by_level.values()), default=1)
    width = margin_x * 2 + (max_level + 1) * box_width + max_level * horizontal_gap
    height = margin_y * 2 + max_rows * box_height + max(max_rows - 1, 0) * vertical_gap

    pixels = bytearray([255, 255, 255] * width * height)
    positions: dict[str, tuple[int, int, int, int]] = {}

    for level in range(max_level + 1):
        level_nodes = rows_by_level.get(level, [])
        for row_index, node in enumerate(level_nodes):
            x1 = margin_x + level * (box_width + horizontal_gap)
            y1 = margin_y + row_index * (box_height + vertical_gap)
            x2 = x1 + box_width
            y2 = y1 + box_height
            positions[node] = (x1, y1, x2, y2)

    edge_color = (55, 90, 140)
    for source, target in lineage:
        if source not in positions or target not in positions:
            continue
        sx1, sy1, sx2, sy2 = positions[source]
        tx1, ty1, tx2, ty2 = positions[target]
        start = (sx2, (sy1 + sy2) // 2)
        end = (tx1, (ty1 + ty2) // 2)
        mid_x = (start[0] + end[0]) // 2
        _draw_line(pixels, width, start[0], start[1], mid_x, start[1], edge_color)
        _draw_line(pixels, width, mid_x, start[1], mid_x, end[1], edge_color)
        _draw_line(pixels, width, mid_x, end[1], end[0], end[1], edge_color)
        _draw_arrow(pixels, width, end[0], end[1], edge_color)

    box_fill = (248, 235, 181)
    box_border = (55, 90, 140)
    text_color = (10, 10, 10)
    for node, (x1, y1, x2, y2) in positions.items():
        _draw_rect(pixels, width, x1, y1, x2, y2, box_fill, box_border)
        _draw_text(
            pixels,
            width,
            x1 + 10,
            y1 + 14,
            node.upper(),
            text_color,
        )

    _write_png(output, width, height, bytes(pixels))


def _ordered_nodes(lineage: list[tuple[str, str]]) -> list[str]:
    """Return nodes in first-seen order."""

    ordered: list[str] = []
    seen: set[str] = set()
    for source, target in lineage:
        for node in (source, target):
            if node in seen:
                continue
            seen.add(node)
            ordered.append(node)
    return ordered


def _assign_levels(
    lineage: list[tuple[str, str]],
    nodes: list[str],
) -> dict[str, int]:
    """Assign a horizontal level to each node from lineage edges."""

    outgoing: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = {node: 0 for node in nodes}

    for source, target in lineage:
        outgoing[source].append(target)
        indegree[target] = indegree.get(target, 0) + 1
        indegree.setdefault(source, 0)

    queue = deque(node for node in nodes if indegree.get(node, 0) == 0)
    levels = {node: 0 for node in nodes}

    while queue:
        node = queue.popleft()
        for target in outgoing.get(node, []):
            levels[target] = max(levels.get(target, 0), levels[node] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)

    return levels


def _draw_rect(
    pixels: bytearray,
    width: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
) -> None:
    """Draw a filled rectangle with a border."""

    for y in range(y1, y2):
        for x in range(x1, x2):
            color = border if x in {x1, x2 - 1} or y in {y1, y2 - 1} else fill
            _set_pixel(pixels, width, x, y, color)


def _draw_line(
    pixels: bytearray,
    width: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, int, int],
) -> None:
    """Draw a straight line using Bresenham's algorithm."""

    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    error = dx + dy

    while True:
        _set_pixel(pixels, width, x1, y1, color)
        if x1 == x2 and y1 == y2:
            break
        error2 = 2 * error
        if error2 >= dy:
            error += dy
            x1 += sx
        if error2 <= dx:
            error += dx
            y1 += sy


def _draw_arrow(
    pixels: bytearray,
    width: int,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    """Draw a simple right-facing arrow head."""

    for offset in range(-3, 4):
        _set_pixel(pixels, width, x, y + offset, color)
    for offset in range(4):
        _set_pixel(pixels, width, x - offset, y - offset, color)
        _set_pixel(pixels, width, x - offset, y + offset, color)


_FONT_5X7 = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "11110", "10001", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
    "F": ["11111", "10000", "11110", "10000", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "11111", "10001", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00001", "00001", "00001", "00001", "10001", "10001", "01110"],
    "K": ["10001", "10010", "11100", "10010", "10001", "10001", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10010", "10001", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "10000", "10000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "_": ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


def _draw_text(
    pixels: bytearray,
    width: int,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
) -> None:
    """Draw text using a simple built-in bitmap font."""

    cursor_x = x
    for character in text:
        glyph = _FONT_5X7.get(character, _FONT_5X7[" "])
        for row_index, row in enumerate(glyph):
            for column_index, bit in enumerate(row):
                if bit == "1":
                    _set_pixel(
                        pixels,
                        width,
                        cursor_x + column_index,
                        y + row_index,
                        color,
                    )
        cursor_x += 6


def _set_pixel(
    pixels: bytearray,
    width: int,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    """Set one pixel if it falls inside the image bounds."""

    if x < 0 or y < 0:
        return

    index = (y * width + x) * 3
    if index < 0 or index + 2 >= len(pixels):
        return

    pixels[index:index + 3] = bytes(color)


def _write_png(output: Path, width: int, height: int, rgb_bytes: bytes) -> None:
    """Write raw RGB bytes as a PNG file."""

    raw_rows = bytearray()
    row_length = width * 3
    for row_start in range(0, len(rgb_bytes), row_length):
        raw_rows.append(0)
        raw_rows.extend(rgb_bytes[row_start:row_start + row_length])

    compressed = zlib.compress(bytes(raw_rows), level=9)
    output.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Return a PNG chunk."""

    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )
