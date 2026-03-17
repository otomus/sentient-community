"""Get historical stock price data for a given ticker symbol."""

import json

try:
    import yfinance as yf
except ImportError:
    yf = None

VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "1y"}


def run(symbol: str, period: str) -> str:
    """Fetch historical OHLCV data for a stock ticker.

    @param symbol: Stock ticker symbol (e.g. 'AAPL').
    @param period: Time period - one of '1d', '5d', '1mo', '3mo', '1y'.
    @returns JSON string with historical price data points.
    @throws ImportError: If yfinance is not installed.
    @throws ValueError: If the period is not valid.
    """
    if yf is None:
        return "error: " + "The 'yfinance' package is required. Install it with: pip install yfinance"

    if period not in VALID_PERIODS:
        raise ValueError(f"Invalid period '{period}'. Must be one of: {', '.join(sorted(VALID_PERIODS))}")

    ticker = yf.Ticker(symbol.upper())
    history = ticker.history(period=period)

    if history.empty:
        raise RuntimeError(f"No historical data found for symbol: {symbol}")

    records = []
    for date, row in history.iterrows():
        records.append({
            "date": str(date.date()),
            "open": round(row["Open"], 2),
            "high": round(row["High"], 2),
            "low": round(row["Low"], 2),
            "close": round(row["Close"], 2),
            "volume": int(row["Volume"]),
        })

    return json.dumps({
        "symbol": symbol.upper(),
        "period": period,
        "data_points": len(records),
        "history": records,
    }, indent=2)
