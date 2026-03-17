"""Search YouTube videos by query."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(query: str, api_key: str, max_results: int = 5) -> str:
    """Search YouTube for videos matching the given query.

    Uses the YouTube Data API v3 search endpoint.

    @param query: Search keywords.
    @param api_key: API key for the YouTube Data API v3.
    @param max_results: Maximum number of results (default 5).
    @returns JSON string with a list of matching videos.
    @throws ValueError: If api_key is not provided.
    @throws RuntimeError: If the API call fails.
    """
    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    if not api_key:
        raise ValueError("api_key is required")

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": api_key,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    videos = [
        {
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
        }
        for item in data.get("items", [])
        if item.get("id", {}).get("videoId")
    ]

    return json.dumps({
        "query": query,
        "count": len(videos),
        "videos": videos,
    }, indent=2)
