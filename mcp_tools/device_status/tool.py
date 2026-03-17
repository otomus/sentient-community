"""Get the status of a connected IoT device."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(device_id: str, device_host: str) -> str:
    """Get the current status of a device from the IoT gateway.

    Calls GET {device_host}/api/v1/devices/{device_id} to retrieve
    the device status including connectivity, battery, and firmware info.

    @param device_id: Unique identifier of the device.
    @param device_host: IoT gateway URL.
    @returns JSON string with the device status.
    @throws ValueError: If device_host is not provided.
    @throws RuntimeError: If the request fails.
    """
    if not device_host:
        raise ValueError("device_host is required")

    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    host = device_host.rstrip("/")
    url = f"{host}/api/v1/devices/{device_id}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    return json.dumps({
        "device_id": device_id,
        "name": data.get("name", ""),
        "status": data.get("status", "unknown"),
        "online": data.get("online", False),
        "battery": data.get("battery"),
        "firmware": data.get("firmware", ""),
        "last_seen": data.get("last_seen", ""),
    }, indent=2)
