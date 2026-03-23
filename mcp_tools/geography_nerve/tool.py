import json
from bs4 import BeautifulSoup
import requests
from tabulate import tabulate

def geography_nerve(data: str, analysis_type: str) -> str:
    """
    Analyzes geographical data to provide insights such as population density, climate patterns, and resource distribution.
    """
    try:
        if analysis_type == "population_density":
            url = f"https://api.population.io/1.0/population/{data}/"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            table = tabulate(data, headers="keys", tablefmt="grid")
            return json.dumps({"analysis_type": analysis_type, "result": table})
        elif analysis_type == "climate_patterns":
            url = f"https://api.openweathermap.org/data/2.5/weather?q={data}&appid=your_api_key"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            table = tabulate([data["weather"], data["main"]], headers="keys", tablefmt="grid")
            return json.dumps({"analysis_type": analysis_type, "result": table})
        elif analysis_type == "resource_distribution":
            url = f"https://api.resourceapi.com/data/{data}/"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            table = tabulate(data, headers="keys", tablefmt="grid")
            return json.dumps({"analysis_type": analysis_type, "result": table})
        else:
            return json.dumps({"error": "Invalid analysis_type"})
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})