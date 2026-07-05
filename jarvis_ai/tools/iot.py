"""Smart-home control. Philips Hue lights are fully implemented against the local Hue
Bridge REST API (no cloud account, works on your LAN). Other device classes (TVs,
thermostats, Nest, CCTVs, generic smart plugs) are left as clearly-marked extension
points — each real vendor needs its own account/API and, in most cases, physical
hardware to test against, so faking them would be worse than an honest "not wired up yet".

Hue setup (one time): the bridge needs you to press its physical link button, then call
pair_hue_bridge() within 30 seconds. It stores an API username in Settings so you only
pair once. Bridge IP is auto-discovered via Philips' discovery service, or set manually.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import requests

import config


def _discover_bridge_ip() -> str:
    manual = config.get_settings().get("hueBridgeIp")
    if manual:
        return manual
    # Philips' hosted discovery returns bridges seen from your public IP on the same LAN.
    res = requests.get("https://discovery.meethue.com/", timeout=8)
    res.raise_for_status()
    bridges = res.json()
    if not bridges:
        raise RuntimeError("No Hue Bridge found on your network. Set its IP manually in Settings.")
    ip = bridges[0]["internalipaddress"]
    config.set_settings({"hueBridgeIp": ip})
    return ip


def pair_hue_bridge() -> str:
    """Press the round button on the Hue Bridge, then call this within 30 seconds."""
    ip = _discover_bridge_ip()
    res = requests.post(f"http://{ip}/api", json={"devicetype": "jarvis_ai#desktop"}, timeout=10)
    data = res.json()
    if isinstance(data, list) and data and "error" in data[0]:
        err = data[0]["error"]
        if err.get("type") == 101:
            raise RuntimeError("Press the link button on top of the Hue Bridge, then try again within 30 seconds.")
        raise RuntimeError(f"Hue pairing failed: {err.get('description')}")
    username = data[0]["success"]["username"]
    config.set_api_keys({"hue": username})
    return "Paired with your Hue Bridge. You can now control your lights."


def _hue_request(method: str, path: str, json_body: Optional[dict] = None):
    username = config.get_api_key("hue")
    if not username:
        raise RuntimeError("Hue isn't paired yet — say \"pair the lights\" after pressing the bridge button.")
    ip = _discover_bridge_ip()
    url = f"http://{ip}/api/{username}{path}"
    res = requests.request(method, url, json=json_body, timeout=8)
    res.raise_for_status()
    return res.json()


def list_lights() -> List[Dict]:
    lights = _hue_request("GET", "/lights")
    return [{"id": lid, "name": info.get("name", lid), "on": info["state"].get("on", False)} for lid, info in lights.items()]


def _find_light_id(name: str) -> Optional[str]:
    for light in list_lights():
        if name.lower() in light["name"].lower():
            return light["id"]
    return None


def set_light(name: Optional[str], on: bool, brightness_percent: Optional[int] = None) -> str:
    state: Dict[str, object] = {"on": on}
    if brightness_percent is not None:
        state["bri"] = max(1, min(254, round(brightness_percent / 100 * 254)))

    if name:
        light_id = _find_light_id(name)
        if not light_id:
            raise RuntimeError(f'No light named "{name}" found.')
        _hue_request("PUT", f"/lights/{light_id}/state", state)
        return f"Turned {'on' if on else 'off'} the {name} light."

    # No name -> apply to every light.
    for light in list_lights():
        _hue_request("PUT", f"/lights/{light['id']}/state", state)
    return f"Turned {'on' if on else 'off'} all lights."


# --- Extension points: not implemented, documented so the command layer can fail cleanly. ---

def control_device(device_class: str, *_args, **_kwargs) -> str:
    raise RuntimeError(
        f"{device_class} control isn't wired up in this build. Philips Hue lights are supported today; "
        "TVs, thermostats, Nest, and CCTVs each need their own vendor account/API — add an adapter in tools/iot.py."
    )
