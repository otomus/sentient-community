"""Read the current temperature and settings from a smart thermostat."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(device_id: str, device_host: str) -> str:
    """Read the thermostat's current temperature and target settings.

    Calls GET {device_host}/api/v1/thermostats/{device_id} to retrieve
    the current and target temperatures along with the operating mode.

    @param device_id: Unique identifier of the thermostat.
    @param device_host: IoT gateway URL.
    @returns JSON string with thermostat readings and settings.
    @throws ValueError: If device_host is not provided.
    @throws RuntimeError: If the request fails.
    """
    if not device_host:
        raise ValueError("device_host is required")

    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    host = device_host.rstrip("/")
    url = f"{host}/api/v1/thermostats/{device_id}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    return json.dumps({
        "device_id": device_id,
        "current_temperature": data.get("current_temperature"),
        "target_temperature": data.get("target_temperature"),
        "unit": data.get("unit", "celsius"),
        "mode": data.get("mode", "auto"),
        "humidity": data.get("humidity"),
        "status": data.get("status", "ok"),
    }, indent=2)
