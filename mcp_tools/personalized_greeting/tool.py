"""Generate personalized greetings based on the time of day."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

MORNING_START_HOUR = 5
AFTERNOON_START_HOUR = 12
EVENING_START_HOUR = 18


def _greeting_for_hour(hour: int) -> str:
    """Return a greeting string based on the hour of day."""
    if MORNING_START_HOUR <= hour < AFTERNOON_START_HOUR:
        return "Good morning! Have a great day ahead!"
    if AFTERNOON_START_HOUR <= hour < EVENING_START_HOUR:
        return "Good afternoon! Keep up the good work!"
    return "Good evening! Have a restful night!"


def run(query: str = "") -> str:
    """Return a time-based greeting, optionally personalized with a name."""
    greeting = _greeting_for_hour(datetime.now().hour)
    if query.strip():
        return f"Hi {query.strip()}, {greeting}"
    return greeting
