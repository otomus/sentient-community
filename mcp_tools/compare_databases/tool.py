import json
import requests
from tinydb import TinyDB, Query

def compare_databases(db1: str, db2: str) -> str:
    """
    Compares two different database systems, highlighting their key differences and use cases.
    """
    try:
        # Fetch descriptions from DuckDuckGo
        url = f"https://api.duckduckgo.com/?q={db1}+database+comparison&format=json"
        response = requests.get(url)
        db1_desc = response.json().get('AbstractText', 'No description available')

        url = f"https://api.duckduckgo.com/?q={db2}+database+comparison&format=json"
        response = requests.get(url)
        db2_desc = response.json().get('AbstractText', 'No description available')

        # Create a simple comparison
        comparison = {
            "db1": {
                "name": db1,
                "description": db1_desc
            },
            "db2": {
                "name": db2,
                "description": db2_desc
            }
        }

        return json.dumps(comparison, indent=4)
    except Exception as e:
        return json.dumps({"error": str(e)})