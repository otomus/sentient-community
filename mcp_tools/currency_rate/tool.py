"""Get the current exchange rate between two currencies."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(from_currency: str, to_currency: str, api_key: str) -> str:
    """Fetch the live exchange rate for a currency pair.

    @param from_currency: ISO 4217 source currency code.
    @param to_currency: ISO 4217 target currency code.
    @param api_key: API key for exchangerate-api.com.
    @returns JSON string containing the exchange rate.
    @throws ValueError: If api_key is not provided.
    @throws RuntimeError: If the API call fails or currency is unsupported.
    """
    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    if not api_key:
        raise ValueError("api_key is required")

    src = from_currency.upper()
    tgt = to_currency.upper()
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{src}/{tgt}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data.get("result") != "success":
        raise RuntimeError(f"Rate lookup failed: {data.get('error-type', 'unknown error')}")

    return json.dumps({
        "from": src,
        "to": tgt,
        "rate": data["conversion_rate"],
        "last_updated": data.get("time_last_update_utc", "unknown"),
    }, indent=2)
