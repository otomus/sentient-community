"""Read and decode QR codes from image files."""


def run(image_path: str) -> str:
    """Read and decode a QR code from an image file.

    @param image_path: Path to the image containing a QR code.
    @returns: Decoded QR code data as a string.
    @throws FileNotFoundError: If the image file does not exist.
    @throws ValueError: If no QR code is found in the image.
    """
    import os

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    decoded_data = _try_pyzbar(image_path)
    if decoded_data is not None:
        return decoded_data

    decoded_data = _try_cv2(image_path)
    if decoded_data is not None:
        return decoded_data

    return "error: " + "No QR code reader available. Install one of: "
        "pip install pyzbar Pillow  OR  pip install opencv-python"


def _try_pyzbar(image_path: str) -> str | None:
    """Attempt to decode using pyzbar and Pillow."""
    try:
        from pyzbar.pyzbar import decode
        from PIL import Image
    except ImportError:
        return None

    img = Image.open(image_path)
    results = decode(img)

    if not results:
        raise ValueError(f"No QR code found in image: {image_path}")

    decoded_values = [result.data.decode("utf-8") for result in results]
    return "\n".join(decoded_values)


def _try_cv2(image_path: str) -> str | None:
    """Attempt to decode using OpenCV's built-in QR detector."""
    try:
        import cv2
    except ImportError:
        return None

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)

    if not data:
        raise ValueError(f"No QR code found in image: {image_path}")

    return data
