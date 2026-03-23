import httpx
import json

def ip_tool(query: str) -> str:
    """
    Fetches the caller's IP location using the ipapi.co API and returns the city, region, country, latitude, and longitude.
    """
    try:
        response = httpx.get("https://ipapi.co/json/")
        response.raise_for_status()
        data = response.json()
        return json.dumps(data)
    except httpx.RequestError as e:
        return json.dumps({"error": str(e)})