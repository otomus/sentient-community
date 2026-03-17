"""Convert Markdown text to HTML using the markdown library."""


def run(markdown_text: str) -> str:
    """
    Convert Markdown-formatted text into HTML.

    Supports standard Markdown extensions: tables, fenced code blocks, and table of contents.

    @param markdown_text: Markdown text to convert.
    @returns: HTML string generated from the Markdown input.
    @throws ImportError: If the markdown library is not installed.
    """
    try:
        import markdown
    except ImportError:
        return "error: " + "markdown is required but not installed. "
            "Install it with: pip install markdown"

    extensions = ["tables", "fenced_code", "toc"]
    html = markdown.markdown(markdown_text, extensions=extensions)
    return html
