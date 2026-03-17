"""Solve mathematical problems including arithmetic, algebra, and word problems."""

import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

MATH_API_URL = "https://api.mathspace.com/solve"
REQUEST_TIMEOUT_SECONDS = 15


def run(query: str) -> str:
    """Send a math problem to the solver API and return the solution."""
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        MATH_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        logger.error("Failed to solve problem: %s", e)
        return f"Error: {e}"

    return data.get("solution", "Error: no solution in response")
