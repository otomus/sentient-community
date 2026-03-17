"""Convert images to ASCII art via an external API."""

import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

ASCII_ART_API_URL = "https://asciiartapi.com/api"
REQUEST_TIMEOUT_SECONDS = 15


def _fetch_image(image_url: str) -> bytes:
    """Download image bytes from a URL."""
    with urllib.request.urlopen(image_url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        return resp.read()


def run(query: str) -> str:
    """Convert an image at the given URL to ASCII art."""
    try:
        image_data = _fetch_image(query)
    except urllib.error.URLError as e:
        logger.error("Failed to fetch image from %s: %s", query, e)
        return f"Error fetching image: {e}"

    req = urllib.request.Request(
        ASCII_ART_API_URL,
        data=image_data,
        headers={"Content-Type": "application/octet-stream"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            return resp.read().decode()
    except urllib.error.URLError as e:
        logger.error("Failed to convert image to ASCII: %s", e)
        return f"Error converting to ASCII: {e}"
