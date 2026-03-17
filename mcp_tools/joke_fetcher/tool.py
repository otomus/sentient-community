"""Fetch random jokes from the JokeAPI (free, no auth required)."""

import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

JOKE_API_BASE_URL = "https://v2.jokeapi.dev/joke"
REQUEST_TIMEOUT_SECONDS = 10


def run(category: str = "Any") -> str:
    """Fetch a random joke. Category can be: Any, Programming, Misc, Pun, Spooky, Christmas."""
    url = f"{JOKE_API_BASE_URL}/{category}?safe-mode"
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        logger.error("Failed to fetch joke: %s", e)
        return f"Error fetching joke: {e}"

    if data.get("type") == "twopart":
        return f"{data['setup']}\n\n{data['delivery']}"
    elif data.get("type") == "single":
        return data["joke"]
    else:
        return f"Error: unexpected response format: {json.dumps(data)}"
