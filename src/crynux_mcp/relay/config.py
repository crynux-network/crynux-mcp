from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any


@dataclass(frozen=True)
class RelayConfig:
    base_url: str
    timeout_seconds: int
    auth_safety_margin_seconds: int
    deposit_addresses: dict[str, str]

    def get_deposit_address(self, network: str) -> str:
        normalized = network.strip().lower()
        direct = self.deposit_addresses.get(normalized, "").strip()
        if direct:
            return direct
        raise ValueError(
            f"MISSING_DEPOSIT_ADDRESS: relay deposit address is not configured for network '{normalized}'."
        )


def load_relay_config() -> RelayConfig:
    data_path = files("crynux_mcp.config").joinpath("relay.json")
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    payload = _cast_dict(raw)

    base_url = str(payload.get("base_url", "")).strip().rstrip("/")
    if not base_url:
        raise ValueError("INVALID_RELAY_CONFIG: base_url is required.")

    timeout_seconds = int(payload.get("timeout_seconds", 10))
    if timeout_seconds <= 0:
        raise ValueError("INVALID_RELAY_CONFIG: timeout_seconds must be greater than 0.")

    auth_safety_margin_seconds = int(payload.get("auth_safety_margin_seconds", 30))
    if auth_safety_margin_seconds < 0:
        raise ValueError("INVALID_RELAY_CONFIG: auth_safety_margin_seconds must be >= 0.")

    deposit_addresses = {
        str(k).strip().lower(): str(v).strip()
        for k, v in _cast_dict(payload.get("deposit_addresses", {})).items()
        if str(k).strip()
    }
    if not deposit_addresses:
        raise ValueError("INVALID_RELAY_CONFIG: deposit_addresses must include at least one network.")

    return RelayConfig(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        auth_safety_margin_seconds=auth_safety_margin_seconds,
        deposit_addresses=deposit_addresses,
    )


def _cast_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("INVALID_RELAY_CONFIG: expected object.")
    return value
