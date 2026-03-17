"""Generate animated GIFs from text descriptions using an external service."""

import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

GIF_SERVICE_URL = "https://api.gif-animation-service.com/generate"
REQUEST_TIMEOUT_SECONDS = 15


def run(query: str) -> str:
    """Generate an animated GIF from a text description and return the URL."""
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        GIF_SERVICE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        logger.error("Failed to generate GIF: %s", e)
        return f"Error generating GIF: {e}"

    return data.get("gif_url", "Error: no gif_url in response")
