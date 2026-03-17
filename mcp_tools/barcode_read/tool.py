"""Read and decode barcodes from image files using pyzbar."""

import os


def run(image_path: str) -> str:
    """Read and decode a barcode from an image file.

    @param image_path: Path to the image containing a barcode.
    @returns: Decoded barcode data and type as a string.
    @throws FileNotFoundError: If the image file does not exist.
    @throws ValueError: If no barcode is found in the image.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    try:
        from pyzbar.pyzbar import decode
        from PIL import Image
    except ImportError:
        return "error: " + "pyzbar and Pillow are required but not installed. "
            "Install them with: pip install pyzbar Pillow"

    img = Image.open(image_path)
    results = decode(img)

    if not results:
        raise ValueError(f"No barcode found in image: {image_path}")

    decoded_entries = _format_results(results)
    return "\n".join(decoded_entries)


def _format_results(results: list) -> list:
    """Format decoded barcode results into readable strings."""
    entries = []
    for result in results:
        barcode_data = result.data.decode("utf-8")
        barcode_type = result.type
        entries.append(f"[{barcode_type}] {barcode_data}")
    return entries
