import requests

def run(query: str) -> str:
    """
    Solves a wide range of mathematical problems, including arithmetic, algebra, and word problems, providing accurate and detailed solutions.
    """
    url = "https://api.mathspace.com/solve"
    headers = {"Content-Type": "application/json"}
    payload = {"query": query}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["solution"]
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"