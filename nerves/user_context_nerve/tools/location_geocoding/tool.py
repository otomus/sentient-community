import requests

def run(query: str) -> str:
    """
    Tool for location geocoding. Returns detailed weather information for any specified location.
    
    Parameters:
    query (str): The location to query.
    
    Returns:
    str: The weather information for the specified location.
    """
    try:
        # Replace 'YOUR_API_KEY' with your actual API key
        api_key = 'YOUR_API_KEY'
        url = f'https://api.openweathermap.org/data/2.5/weather?q={query}&appid={api_key}&units=metric'
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        temperature = data['main']['temp']
        weather = data['weather'][0]['description']
        return f'Temperature: {temperature}°C, Weather: {weather}'
    except requests.RequestException as e:
        return f'Error: {e}'