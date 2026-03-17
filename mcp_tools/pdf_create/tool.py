"""Create a PDF file from text content using reportlab."""

import os


PAGE_WIDTH = 595.27
PAGE_HEIGHT = 841.89
MARGIN = 72
FONT_NAME = "Helvetica"
FONT_SIZE = 12
LINE_HEIGHT = 14


def run(file_path: str, content: str) -> str:
    """
    Create a PDF file containing the provided text content.

    @param file_path: Output path for the PDF file.
    @param content: Text content to write into the PDF.
    @returns: Confirmation message with the output path.
    @throws ImportError: If reportlab is not installed.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return "error: " + "reportlab is required but not installed. "
            "Install it with: pip install reportlab"

    resolved = os.path.abspath(file_path)
    parent_dir = os.path.dirname(resolved)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    page_width, page_height = A4
    usable_width = page_width - 2 * MARGIN

    pdf_canvas = canvas.Canvas(resolved, pagesize=A4)
    pdf_canvas.setFont(FONT_NAME, FONT_SIZE)

    lines = content.split("\n")
    y_position = page_height - MARGIN

    for line in lines:
        wrapped = _wrap_text(pdf_canvas, line, usable_width)
        for wrapped_line in wrapped:
            if y_position < MARGIN:
                pdf_canvas.showPage()
                pdf_canvas.setFont(FONT_NAME, FONT_SIZE)
                y_position = page_height - MARGIN
            pdf_canvas.drawString(MARGIN, y_position, wrapped_line)
            y_position -= LINE_HEIGHT

    pdf_canvas.save()
    return f"PDF created successfully at: {resolved}"


def _wrap_text(pdf_canvas: object, text: str, max_width: float) -> list[str]:
    """Break a line of text into wrapped lines that fit within max_width."""
    if not text:
        return [""]

    words = text.split(" ")
    lines: list[str] = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        width = pdf_canvas.stringWidth(test_line, FONT_NAME, FONT_SIZE)
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]
