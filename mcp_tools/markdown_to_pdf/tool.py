"""Convert Markdown text to a PDF file using markdown and reportlab."""

import os
import re


FONT_NAME = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"
FONT_SIZE_BODY = 12
FONT_SIZE_H1 = 24
FONT_SIZE_H2 = 20
FONT_SIZE_H3 = 16
LINE_HEIGHT = 14
MARGIN = 72


def run(markdown_text: str, output_path: str) -> str:
    """
    Convert Markdown text to a PDF file.

    Renders headings (h1-h3), paragraphs, and bullet lists.
    For full HTML rendering, consider using weasyprint instead.

    @param markdown_text: Markdown text to convert.
    @param output_path: Output path for the generated PDF file.
    @returns: Confirmation message with the output path.
    @throws ImportError: If reportlab is not installed.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return "error: " + "reportlab is required but not installed. "
            "Install it with: pip install reportlab"

    resolved = os.path.abspath(output_path)
    parent_dir = os.path.dirname(resolved)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    page_width, page_height = A4
    pdf_canvas = canvas.Canvas(resolved, pagesize=A4)
    y_position = page_height - MARGIN

    lines = markdown_text.split("\n")

    for line in lines:
        font_name, font_size, text = _parse_line(line)

        if y_position < MARGIN:
            pdf_canvas.showPage()
            y_position = page_height - MARGIN

        pdf_canvas.setFont(font_name, font_size)
        pdf_canvas.drawString(MARGIN, y_position, text)
        y_position -= font_size + 4

    pdf_canvas.save()
    return f"PDF created from Markdown at: {resolved}"


def _parse_line(line: str) -> tuple[str, int, str]:
    """
    Determine font style and cleaned text for a Markdown line.

    Returns a tuple of (font_name, font_size, cleaned_text).
    """
    stripped = line.strip()

    if stripped.startswith("### "):
        return FONT_NAME_BOLD, FONT_SIZE_H3, stripped[4:]
    if stripped.startswith("## "):
        return FONT_NAME_BOLD, FONT_SIZE_H2, stripped[3:]
    if stripped.startswith("# "):
        return FONT_NAME_BOLD, FONT_SIZE_H1, stripped[2:]
    if stripped.startswith("- ") or stripped.startswith("* "):
        return FONT_NAME, FONT_SIZE_BODY, f"  \u2022 {stripped[2:]}"

    # Strip bold/italic markers for plain rendering
    cleaned = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", stripped)
    return FONT_NAME, FONT_SIZE_BODY, cleaned
