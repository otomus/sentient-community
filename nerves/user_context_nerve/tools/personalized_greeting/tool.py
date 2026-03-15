import requests
from datetime import datetime

def run(query: str) -> str:
    """Provides an engaging and encouraging morning greeting based on the time of day."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        greeting = "Good morning! Have a great day ahead!"
    elif 12 <= current_hour < 18:
        greeting = "Good afternoon! Keep up the good work!"
    else:
        greeting = "Good evening! Have a restful night!"
    return greeting