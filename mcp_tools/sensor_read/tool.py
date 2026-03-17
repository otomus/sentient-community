"""Read the current value from an IoT sensor."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(sensor_id: str, device_host: str) -> str:
    """Read the current value from a sensor via the IoT gateway REST API.

    Calls GET {device_host}/api/v1/sensors/{sensor_id} to retrieve
    the latest reading.

    @param sensor_id: Unique identifier of the sensor.
    @param device_host: IoT gateway URL.
    @returns JSON string with the sensor reading.
    @throws ValueError: If device_host is not provided.
    @throws RuntimeError: If the request fails.
    """
    if not device_host:
        raise ValueError("device_host is required")

    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    host = device_host.rstrip("/")
    url = f"{host}/api/v1/sensors/{sensor_id}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    return json.dumps({
        "sensor_id": sensor_id,
        "value": data.get("value"),
        "unit": data.get("unit", ""),
        "timestamp": data.get("timestamp", ""),
        "status": data.get("status", "ok"),
    }, indent=2)
