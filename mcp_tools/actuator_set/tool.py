"""Set the value of an IoT actuator."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(actuator_id: str, value: str, device_host: str) -> str:
    """Set an actuator to the specified value via the IoT gateway.

    Calls POST {device_host}/api/v1/actuators/{actuator_id} with the
    desired value in the request body.

    @param actuator_id: Unique identifier of the actuator.
    @param value: The value to set.
    @param device_host: IoT gateway URL.
    @returns JSON string confirming the actuator state change.
    @throws ValueError: If device_host is not provided.
    @throws RuntimeError: If the request fails.
    """
    if not device_host:
        raise ValueError("device_host is required")

    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    host = device_host.rstrip("/")
    url = f"{host}/api/v1/actuators/{actuator_id}"

    response = requests.post(url, json={"value": value}, timeout=10)
    response.raise_for_status()
    data = response.json()

    return json.dumps({
        "actuator_id": actuator_id,
        "value": value,
        "status": data.get("status", "ok"),
        "previous_value": data.get("previous_value"),
    }, indent=2)
