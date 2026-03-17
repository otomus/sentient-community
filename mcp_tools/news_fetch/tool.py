"""Fetch news articles matching a search query."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(query: str, api_key: str, count: int = 5) -> str:
    """Fetch news articles from NewsAPI matching the given query.

    @param query: Search keywords for finding relevant articles.
    @param api_key: API key for NewsAPI.
    @param count: Maximum number of articles to return (default 5).
    @returns JSON string with a list of article titles, sources, and URLs.
    @throws ValueError: If api_key is not provided.
    @throws RuntimeError: If the API call fails.
    """
    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    if not api_key:
        raise ValueError("api_key is required")

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "pageSize": count,
        "sortBy": "publishedAt",
        "apiKey": api_key,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "ok":
        raise RuntimeError(f"News fetch failed: {data.get('message', 'unknown error')}")

    articles = [
        {
            "title": article["title"],
            "source": article["source"]["name"],
            "url": article["url"],
            "published_at": article["publishedAt"],
            "description": article.get("description", ""),
        }
        for article in data.get("articles", [])
    ]

    return json.dumps({
        "query": query,
        "total_results": data.get("totalResults", 0),
        "articles": articles,
    }, indent=2)
