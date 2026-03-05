from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any


@dataclass(frozen=True)
class NativeCurrency:
    name: str
    symbol: str
    decimals: int


@dataclass(frozen=True)
class ChainConfig:
    network_key: str
    chain_id: int
    chain_name: str
    rpc_url: str
    native_currency: NativeCurrency
    contracts: dict[str, str]


class ChainRegistry:
    def __init__(self, default_network: str, networks: dict[str, ChainConfig]) -> None:
        self.default_network = default_network
        self.networks = networks

    def resolve(self, network: str | None) -> ChainConfig:
        selected = (network or self.default_network).strip().lower()
        if selected not in self.networks:
            available = ", ".join(sorted(self.networks))
            raise ValueError(f"INVALID_NETWORK: '{selected}' is not supported. Supported: {available}.")
        return self.networks[selected]


def load_chain_registry() -> ChainRegistry:
    data_path = files("crynux_mcp.config").joinpath("chains.json")
    raw = json.loads(data_path.read_text(encoding="utf-8"))

    default_network = str(raw["default_network"]).strip().lower()
    parsed: dict[str, ChainConfig] = {}
    for network_key, cfg in cast_dict(raw["networks"]).items():
        rpc_urls = cfg.get("rpc_urls", [])
        if not rpc_urls:
            raise ValueError(f"INVALID_CONFIG: network '{network_key}' has no rpc_urls.")
        native = cast_dict(cfg["native_currency"])
        parsed[network_key] = ChainConfig(
            network_key=network_key,
            chain_id=int(cfg["chain_id"]),
            chain_name=str(cfg["chain_name"]),
            rpc_url=str(rpc_urls[0]),
            native_currency=NativeCurrency(
                name=str(native["name"]),
                symbol=str(native["symbol"]),
                decimals=int(native["decimals"]),
            ),
            contracts={k: str(v) for k, v in cast_dict(cfg.get("contracts", {})).items()},
        )

    if default_network not in parsed:
        raise ValueError("INVALID_CONFIG: default_network must exist in networks.")
    return ChainRegistry(default_network=default_network, networks=parsed)


def cast_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("INVALID_CONFIG: expected object.")
    return value
