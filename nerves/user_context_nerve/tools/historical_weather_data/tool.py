import requests

def run(query: str) -> str:
    """
    Provides detailed weather information for a specified location.
    
    Args:
    query (str): The location to get weather data for.
    
    Returns:
    str: A string containing the weather details.
    """
    url = f"http://api.weatherapi.com/v1/current.json?key=YOUR_API_KEY&q={query}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        temp_c = data['current']['temp_c']
        condition = data['current']['condition']['text']
        return f"Temperature: {temp_c}°C, Condition: {condition}"
    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data: {e}"