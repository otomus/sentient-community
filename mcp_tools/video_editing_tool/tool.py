"""Generate animated GIFs from text descriptions using external video editing services."""

import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

GIF_API_URL = "https://api.example.com/generate_gif"
REQUEST_TIMEOUT_SECONDS = 15


def run(query: str) -> str:
    """Generate an animated GIF from a text description and return the URL."""
    payload = json.dumps({"text": query}).encode()
    req = urllib.request.Request(
        GIF_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        logger.error("Failed to generate GIF: %s", e)
        return f"Error: {e}"

    return data.get("gif_url", "Error: no gif_url in response")
