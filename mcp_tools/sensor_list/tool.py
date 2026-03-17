"""List all available sensors on the IoT gateway."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(device_host: str) -> str:
    """List all sensors registered on the IoT gateway.

    Calls GET {device_host}/api/v1/sensors to retrieve the full sensor list.

    @param device_host: IoT gateway URL.
    @returns JSON string with a list of available sensors.
    @throws ValueError: If device_host is not provided.
    @throws RuntimeError: If the request fails.
    """
    if not device_host:
        raise ValueError("device_host is required")

    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    host = device_host.rstrip("/")
    url = f"{host}/api/v1/sensors"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    sensors = data if isinstance(data, list) else data.get("sensors", [])

    return json.dumps({
        "host": host,
        "count": len(sensors),
        "sensors": sensors,
    }, indent=2)
