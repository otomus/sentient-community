import json
import requests
from bs4 import BeautifulSoup
import yaml

def parse_geographical_data(data: str, question: str) -> str:
    """
    Parses geographical data to answer questions about locations, coordinates, and regions.
    """
    try:
        # Parse the input data
        parsed_data = yaml.safe_load(data)
        
        # Example: Extract coordinates from a location
        if "coordinates" in question:
            location = question.split("coordinates of ")[1]
            if location in parsed_data:
                return json.dumps(parsed_data[location])
            else:
                return json.dumps({"error": f"Location '{location}' not found"})
        
        # Example: Extract region information
        elif "region" in question:
            location = question.split("region of ")[1]
            if location in parsed_data:
                return json.dumps(parsed_data[location]["region"])
            else:
                return json.dumps({"error": f"Location '{location}' not found"})
        
        else:
            return json.dumps({"error": "Unsupported question type"})
    
    except yaml.YAMLError as e:
        return json.dumps({"error": f"YAML parsing error: {e}"})
    except Exception as e:
        return json.dumps({"error": f"An error occurred: {e}"})