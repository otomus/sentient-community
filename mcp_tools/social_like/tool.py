"""Like a social media post on a specified platform."""

import json

try:
    import requests
except ImportError:
    requests = None

PLATFORM_ENDPOINTS = {
    "twitter": "https://api.twitter.com/2/users/{user_id}/likes",
    "mastodon": "{instance}/api/v1/statuses/{post_id}/favourite",
}


def run(platform: str, post_id: str, api_key: str, instance_url: str = "") -> str:
    """Like a post on the specified social media platform.

    @param platform: Name of the social media platform.
    @param post_id: Unique identifier of the post to like.
    @param api_key: API key or access token for the platform.
    @param instance_url: Mastodon instance URL (e.g. 'https://mastodon.social'). Required for Mastodon.
    @returns JSON string confirming the like action.
    @throws ValueError: If api_key is not provided.
    @throws RuntimeError: If the API call fails or platform is unsupported.
    """
    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    if not api_key:
        raise ValueError("api_key is required")

    platform_lower = platform.lower()

    if platform_lower == "twitter":
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.post(
            "https://api.twitter.com/2/users/me/likes",
            json={"tweet_id": post_id},
            headers=headers,
            timeout=10,
        )
    elif platform_lower == "mastodon":
        instance = instance_url or "https://mastodon.social"
        url = f"{instance}/api/v1/statuses/{post_id}/favourite"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.post(url, headers=headers, timeout=10)
    else:
        raise RuntimeError(f"Unsupported platform: {platform}. Supported: twitter, mastodon")

    response.raise_for_status()

    return json.dumps({
        "status": "liked",
        "platform": platform_lower,
        "post_id": post_id,
    }, indent=2)
