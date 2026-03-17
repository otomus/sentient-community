"""Process voice recognition queries using an external API."""

import json
import logging
import urllib.request
import urllib.error
import urllib.parse

logger = logging.getLogger(__name__)

VOICE_API_URL = "https://api.example.com/voice_recognition"
REQUEST_TIMEOUT_SECONDS = 15


def run(query: str) -> str:
    """Send a voice recognition query and return the result."""
    params = urllib.parse.urlencode({"query": query})
    url = f"{VOICE_API_URL}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        logger.error("Failed to process voice recognition: %s", e)
        return f"Error: {e}"

    return data.get("result", "Error: no result in response")
