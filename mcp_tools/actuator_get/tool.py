"""Get the current state of an IoT actuator."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(actuator_id: str, device_host: str) -> str:
    """Get the current state of an actuator from the IoT gateway.

    Calls GET {device_host}/api/v1/actuators/{actuator_id} to retrieve
    the current actuator value and status.

    @param actuator_id: Unique identifier of the actuator.
    @param device_host: IoT gateway URL.
    @returns JSON string with the actuator state.
    @throws ValueError: If device_host is not provided.
    @throws RuntimeError: If the request fails.
    """
    if not device_host:
        raise ValueError("device_host is required")

    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    host = device_host.rstrip("/")
    url = f"{host}/api/v1/actuators/{actuator_id}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    return json.dumps({
        "actuator_id": actuator_id,
        "value": data.get("value"),
        "status": data.get("status", "ok"),
        "last_updated": data.get("last_updated", ""),
    }, indent=2)
