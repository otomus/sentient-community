"""Get follower count and list for a social media user."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(platform: str, username: str, api_key: str, instance_url: str = "") -> str:
    """Fetch the follower count for a user on the specified platform.

    @param platform: Name of the social media platform.
    @param username: The username to look up.
    @param api_key: API key or access token for the platform.
    @param instance_url: Mastodon instance URL (e.g. 'https://mastodon.social'). Required for Mastodon.
    @returns JSON string with follower count and user info.
    @throws ValueError: If api_key is not provided.
    @throws RuntimeError: If the API call fails or platform is unsupported.
    """
    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    if not api_key:
        raise ValueError("api_key is required")

    platform_lower = platform.lower()

    if platform_lower == "twitter":
        url = f"https://api.twitter.com/2/users/by/username/{username}"
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"user.fields": "public_metrics"}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", {})
        metrics = data.get("public_metrics", {})
        return json.dumps({
            "platform": platform_lower,
            "username": username,
            "followers": metrics.get("followers_count", 0),
            "following": metrics.get("following_count", 0),
        }, indent=2)

    if platform_lower == "mastodon":
        instance = instance_url or "https://mastodon.social"
        lookup_url = f"{instance}/api/v1/accounts/lookup"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(lookup_url, params={"acct": username}, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return json.dumps({
            "platform": platform_lower,
            "username": username,
            "followers": data.get("followers_count", 0),
            "following": data.get("following_count", 0),
            "display_name": data.get("display_name", ""),
        }, indent=2)

    raise RuntimeError(f"Unsupported platform: {platform}. Supported: twitter, mastodon")
