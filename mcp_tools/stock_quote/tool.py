"""Get the current stock quote for a given ticker symbol."""

import json

try:
    import yfinance as yf
except ImportError:
    yf = None


def run(symbol: str) -> str:
    """Fetch the latest stock quote using yfinance.

    @param symbol: Stock ticker symbol (e.g. 'AAPL').
    @returns JSON string with current price, change, and volume.
    @throws ImportError: If yfinance is not installed.
    @throws RuntimeError: If the ticker symbol is invalid.
    """
    if yf is None:
        return "error: " + "The 'yfinance' package is required. Install it with: pip install yfinance"

    ticker = yf.Ticker(symbol.upper())
    info = ticker.info

    if not info or info.get("regularMarketPrice") is None:
        raise RuntimeError(f"No quote data found for symbol: {symbol}")

    return json.dumps({
        "symbol": symbol.upper(),
        "name": info.get("shortName", ""),
        "price": info.get("regularMarketPrice"),
        "previous_close": info.get("regularMarketPreviousClose"),
        "change": info.get("regularMarketChange"),
        "change_percent": info.get("regularMarketChangePercent"),
        "volume": info.get("regularMarketVolume"),
        "market_cap": info.get("marketCap"),
        "currency": info.get("currency", "USD"),
    }, indent=2)
