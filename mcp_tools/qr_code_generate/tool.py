"""Generate QR code images from text or URL data."""

import os


def run(data: str, output_path: str, size: int = 10) -> str:
    """Generate a QR code image and save it to a file.

    @param data: The data to encode (text, URL, etc.).
    @param output_path: File path for the output QR code image.
    @param size: Box size in pixels for each QR module.
    @returns: Confirmation message with the output path.
    @throws ValueError: If data is empty or size is invalid.
    """
    try:
        import qrcode
    except ImportError:
        return "error: " + "qrcode is required but not installed. "
            "Install it with: pip install qrcode[pil]"

    if not data.strip():
        raise ValueError("Data cannot be empty")

    if size < 1:
        raise ValueError("Size must be a positive integer")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    img.save(output_path)

    return f"QR code saved to {output_path}"
