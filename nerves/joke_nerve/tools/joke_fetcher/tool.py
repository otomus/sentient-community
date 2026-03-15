"""Fetch random jokes from the JokeAPI (free, no auth required)."""

import json
import urllib.request
import urllib.error


def run(category: str = "Any") -> str:
    """Fetch a random joke. Category can be: Any, Programming, Misc, Pun, Spooky, Christmas."""
    url = f"https://v2.jokeapi.dev/joke/{category}?safe-mode"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        return f"Error fetching joke: {e}"

    if data.get("type") == "twopart":
        return f"{data['setup']}\n\n{data['delivery']}"
    elif data.get("type") == "single":
        return data["joke"]
    else:
        return f"Error: unexpected response format: {json.dumps(data)}"
