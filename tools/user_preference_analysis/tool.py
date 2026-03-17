"""Analyze user data for demographic insights and preference profiling."""

import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

ANALYSIS_API_URL = "https://api.userpreferenceanalysis.com/analyze"
REQUEST_TIMEOUT_SECONDS = 15


def run(query: str) -> str:
    """Send a query to the user preference analysis API and return the result."""
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        ANALYSIS_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            return resp.read().decode()
    except urllib.error.URLError as e:
        logger.error("Failed to analyze user preferences: %s", e)
        return f"Error: {e}"
