"""Read text content from a DOCX file using python-docx."""

import os


def run(file_path: str) -> str:
    """
    Extract all text content from a DOCX file.

    @param file_path: Path to the DOCX file to read.
    @returns: Extracted text with paragraphs separated by newlines.
    @throws FileNotFoundError: If the DOCX file does not exist.
    @throws ImportError: If python-docx is not installed.
    """
    try:
        import docx
    except ImportError:
        return "error: " + "python-docx is required but not installed. "
            "Install it with: pip install python-docx"

    resolved = os.path.abspath(file_path)
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"DOCX file not found: {resolved}")

    document = docx.Document(resolved)
    paragraphs = [paragraph.text for paragraph in document.paragraphs]

    if not any(paragraphs):
        return "No text content found in the DOCX file."

    return "\n".join(paragraphs)
