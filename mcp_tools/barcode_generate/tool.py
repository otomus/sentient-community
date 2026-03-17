"""Generate barcode images in various formats."""

import os

SUPPORTED_BARCODE_TYPES = ("code128", "ean13", "upc")

BARCODE_TYPE_MAP = {
    "code128": "code128",
    "ean13": "ean13",
    "upc": "upca",
}


def run(data: str, output_path: str, barcode_type: str = "code128") -> str:
    """Generate a barcode image and save it to a file.

    @param data: The data to encode in the barcode.
    @param output_path: File path for the output barcode image.
    @param barcode_type: Barcode format: code128, ean13, or upc.
    @returns: Confirmation message with the output path.
    @throws ValueError: If data is empty or barcode_type is unsupported.
    """
    try:
        import barcode as barcode_lib
        from barcode.writer import ImageWriter
    except ImportError:
        return "error: " + "python-barcode is required but not installed. "
            "Install it with: pip install python-barcode Pillow"

    if not data.strip():
        raise ValueError("Data cannot be empty")

    if barcode_type not in SUPPORTED_BARCODE_TYPES:
        raise ValueError(
            f"Unsupported barcode type: {barcode_type}. "
            f"Supported types: {', '.join(SUPPORTED_BARCODE_TYPES)}"
        )

    internal_type = BARCODE_TYPE_MAP[barcode_type]
    barcode_class = barcode_lib.get_barcode_class(internal_type)

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # python-barcode appends the extension automatically,
    # so strip it to avoid double extensions
    base_path = _strip_image_extension(output_path)

    writer = ImageWriter()
    barcode_instance = barcode_class(data, writer=writer)
    saved_path = barcode_instance.save(base_path)

    return f"Barcode saved to {saved_path}"


def _strip_image_extension(path: str) -> str:
    """Remove common image extensions so python-barcode can add its own."""
    for ext in (".png", ".svg", ".jpg", ".jpeg"):
        if path.lower().endswith(ext):
            return path[: -len(ext)]
    return path
