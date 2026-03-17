"""Create diagrams from text definitions and save as SVG or PNG."""

import os
import re

SUPPORTED_DIAGRAM_TYPES = ("flowchart", "sequence", "class")


def run(diagram_type: str, definition: str, output_path: str) -> str:
    """Create a diagram from a text definition and save it to a file.

    @param diagram_type: Type of diagram (flowchart, sequence, class).
    @param definition: Text definition describing the diagram structure.
    @param output_path: File path for the output image (.svg or .png).
    @returns: Confirmation message with the output path.
    @throws ValueError: If diagram_type is unsupported or definition is empty.
    """
    if diagram_type not in SUPPORTED_DIAGRAM_TYPES:
        raise ValueError(
            f"Unsupported diagram type: {diagram_type}. "
            f"Supported types: {', '.join(SUPPORTED_DIAGRAM_TYPES)}"
        )

    if not definition.strip():
        raise ValueError("Diagram definition cannot be empty")

    svg_content = _generate_svg(diagram_type, definition)

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if output_path.endswith(".png"):
        _save_as_png(svg_content, output_path)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

    return f"Diagram saved to {output_path}"


def _generate_svg(diagram_type: str, definition: str) -> str:
    """Generate SVG content based on diagram type and definition."""
    if diagram_type == "flowchart":
        return _generate_flowchart_svg(definition)
    elif diagram_type == "sequence":
        return _generate_sequence_svg(definition)
    elif diagram_type == "class":
        return _generate_class_svg(definition)
    raise ValueError(f"Unknown diagram type: {diagram_type}")


def _generate_flowchart_svg(definition: str) -> str:
    """Generate a flowchart SVG from 'A -> B -> C' style definitions."""
    nodes = _parse_flowchart_nodes(definition)
    box_width = 120
    box_height = 40
    margin_y = 30
    padding = 20

    total_height = len(nodes) * (box_height + margin_y) + padding
    svg_width = box_width + padding * 2
    center_x = svg_width // 2

    elements = []
    for i, node in enumerate(nodes):
        y = padding + i * (box_height + margin_y)
        x = center_x - box_width // 2
        elements.append(
            f'  <rect x="{x}" y="{y}" width="{box_width}" '
            f'height="{box_height}" rx="5" ry="5" '
            f'fill="#4A90D9" stroke="#2C5F8A" stroke-width="1.5"/>'
        )
        text_y = y + box_height // 2 + 5
        elements.append(
            f'  <text x="{center_x}" y="{text_y}" '
            f'text-anchor="middle" fill="white" '
            f'font-family="Arial" font-size="14">{_escape_xml(node)}</text>'
        )
        if i < len(nodes) - 1:
            arrow_y_start = y + box_height
            arrow_y_end = y + box_height + margin_y
            elements.append(
                f'  <line x1="{center_x}" y1="{arrow_y_start}" '
                f'x2="{center_x}" y2="{arrow_y_end}" '
                f'stroke="#333" stroke-width="2" marker-end="url(#arrowhead)"/>'
            )

    return _wrap_svg(svg_width, total_height, "\n".join(elements))


def _generate_sequence_svg(definition: str) -> str:
    """Generate a sequence diagram SVG from 'A -> B: message' lines."""
    lines = [line.strip() for line in definition.strip().splitlines() if line.strip()]
    participants = _extract_sequence_participants(lines)
    spacing = 160
    svg_width = len(participants) * spacing + 40
    header_y = 30
    row_height = 50

    elements = []
    for i, participant in enumerate(participants):
        x = 40 + i * spacing
        elements.append(
            f'  <rect x="{x - 40}" y="{header_y - 15}" width="80" '
            f'height="30" rx="3" fill="#4A90D9" stroke="#2C5F8A"/>'
        )
        elements.append(
            f'  <text x="{x}" y="{header_y + 5}" text-anchor="middle" '
            f'fill="white" font-family="Arial" font-size="12">'
            f'{_escape_xml(participant)}</text>'
        )
        line_top = header_y + 15
        line_bottom = header_y + 15 + len(lines) * row_height + 20
        elements.append(
            f'  <line x1="{x}" y1="{line_top}" x2="{x}" y2="{line_bottom}" '
            f'stroke="#999" stroke-width="1" stroke-dasharray="4,4"/>'
        )

    for i, line in enumerate(lines):
        match = re.match(r"(\w+)\s*->\s*(\w+)\s*:\s*(.*)", line)
        if not match:
            continue
        src, dst, msg = match.groups()
        if src not in participants or dst not in participants:
            continue
        src_x = 40 + participants.index(src) * spacing
        dst_x = 40 + participants.index(dst) * spacing
        y = header_y + 40 + i * row_height
        elements.append(
            f'  <line x1="{src_x}" y1="{y}" x2="{dst_x}" y2="{y}" '
            f'stroke="#333" stroke-width="1.5" marker-end="url(#arrowhead)"/>'
        )
        mid_x = (src_x + dst_x) // 2
        elements.append(
            f'  <text x="{mid_x}" y="{y - 8}" text-anchor="middle" '
            f'font-family="Arial" font-size="11" fill="#333">'
            f'{_escape_xml(msg)}</text>'
        )

    total_height = header_y + 15 + len(lines) * row_height + 40
    return _wrap_svg(svg_width, total_height, "\n".join(elements))


def _generate_class_svg(definition: str) -> str:
    """Generate a class diagram SVG from 'ClassName: method1, method2' lines."""
    lines = [line.strip() for line in definition.strip().splitlines() if line.strip()]
    box_width = 180
    margin = 20
    y_offset = 20

    elements = []
    for line in lines:
        parts = line.split(":", 1)
        class_name = parts[0].strip()
        methods = [m.strip() for m in parts[1].split(",")] if len(parts) > 1 else []

        header_height = 30
        method_height = 20 * max(len(methods), 1)
        box_height = header_height + method_height + 10

        elements.append(
            f'  <rect x="{margin}" y="{y_offset}" width="{box_width}" '
            f'height="{box_height}" fill="white" stroke="#333" stroke-width="1.5"/>'
        )
        elements.append(
            f'  <rect x="{margin}" y="{y_offset}" width="{box_width}" '
            f'height="{header_height}" fill="#4A90D9" stroke="#333" stroke-width="1.5"/>'
        )
        elements.append(
            f'  <text x="{margin + box_width // 2}" y="{y_offset + 20}" '
            f'text-anchor="middle" fill="white" font-family="Arial" '
            f'font-size="13" font-weight="bold">{_escape_xml(class_name)}</text>'
        )
        for j, method in enumerate(methods):
            method_y = y_offset + header_height + 18 + j * 20
            elements.append(
                f'  <text x="{margin + 10}" y="{method_y}" '
                f'font-family="Arial" font-size="11" fill="#333">'
                f'{_escape_xml(method)}</text>'
            )

        y_offset += box_height + margin

    total_height = y_offset + margin
    svg_width = box_width + margin * 2
    return _wrap_svg(svg_width, total_height, "\n".join(elements))


def _parse_flowchart_nodes(definition: str) -> list:
    """Extract node names from 'A -> B -> C' syntax."""
    return [node.strip() for node in re.split(r"\s*->\s*", definition) if node.strip()]


def _extract_sequence_participants(lines: list) -> list:
    """Extract unique participant names from sequence lines."""
    participants = []
    for line in lines:
        match = re.match(r"(\w+)\s*->\s*(\w+)", line)
        if match:
            for name in match.groups():
                if name not in participants:
                    participants.append(name)
    return participants


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _wrap_svg(width: int, height: int, content: str) -> str:
    """Wrap SVG content with the root element and arrowhead marker."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f"  <defs>\n"
        f'    <marker id="arrowhead" markerWidth="10" markerHeight="7" '
        f'refX="10" refY="3.5" orient="auto">\n'
        f'      <polygon points="0 0, 10 3.5, 0 7" fill="#333"/>\n'
        f"    </marker>\n"
        f"  </defs>\n"
        f"{content}\n"
        f"</svg>"
    )


def _save_as_png(svg_content: str, output_path: str) -> None:
    """Convert SVG content to PNG using cairosvg if available, else save as SVG."""
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_content.encode("utf-8"), write_to=output_path)
    except ImportError:
        # Fall back to saving as SVG with .png extension note
        svg_path = output_path.rsplit(".", 1)[0] + ".svg"
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        return (
            f"error: cairosvg is required for PNG output. SVG saved to {svg_path} instead. "
            "Install cairosvg with: pip install cairosvg"
        )
