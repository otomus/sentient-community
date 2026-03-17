"""Create a DOCX file from text content using python-docx."""

import os


def run(file_path: str, content: str) -> str:
    """
    Create a DOCX file containing the provided text content.

    Each line in the content becomes a separate paragraph in the document.

    @param file_path: Output path for the DOCX file.
    @param content: Text content to write, with newlines separating paragraphs.
    @returns: Confirmation message with the output path.
    @throws ImportError: If python-docx is not installed.
    """
    try:
        import docx
    except ImportError:
        return "error: " + "python-docx is required but not installed. "
            "Install it with: pip install python-docx"

    resolved = os.path.abspath(file_path)
    parent_dir = os.path.dirname(resolved)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    document = docx.Document()
    lines = content.split("\n")

    for line in lines:
        document.add_paragraph(line)

    document.save(resolved)
    return f"DOCX created successfully at: {resolved}"
