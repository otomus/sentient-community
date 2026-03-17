"""Read text content from a PDF file using pdfplumber."""

import os


def run(file_path: str) -> str:
    """
    Extract all text content from a PDF file.

    @param file_path: Path to the PDF file to read.
    @returns: Extracted text from all pages, separated by page breaks.
    @throws FileNotFoundError: If the PDF file does not exist.
    @throws ImportError: If pdfplumber is not installed.
    """
    try:
        import pdfplumber
    except ImportError:
        return "error: " + "pdfplumber is required but not installed. "
            "Install it with: pip install pdfplumber"

    resolved = os.path.abspath(file_path)
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"PDF file not found: {resolved}")

    pages_text: list[str] = []
    with pdfplumber.open(resolved) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                pages_text.append(f"--- Page {page_number} ---\n{text}")

    if not pages_text:
        return "No text content found in the PDF."

    return "\n\n".join(pages_text)
