from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Literal

from crynux_mcp.config.loader import ChainConfig

RelayEnvName = Literal["staging", "production"]
VALID_RELAY_ENVS = frozenset({"staging", "production"})
RELAY_ENV_REQUIRED_NETWORK_KIND: dict[str, str] = {
    "staging": "testnet",
    "production": "mainnet",
}


@dataclass(frozen=True)
class RelayEnvironmentConfig:
    base_url: str
    deposit_address: str


@dataclass(frozen=True)
class RelayConfig:
    default_env: str
    timeout_seconds: int
    auth_safety_margin_seconds: int
    environments: dict[str, RelayEnvironmentConfig]

    def resolve_env(self, relay_env: str | None = None) -> tuple[str, RelayEnvironmentConfig]:
        selected = (relay_env or self.default_env).strip().lower()
        if selected not in self.environments:
            available = ", ".join(sorted(self.environments))
            raise ValueError(
                f"INVALID_RELAY_ENV: '{selected}' is not supported. Supported: {available}."
            )
        return selected, self.environments[selected]

    def get_base_url(self, relay_env: str | None = None, relay_base_url: str | None = None) -> str:
        override = (relay_base_url or "").strip().rstrip("/")
        if override:
            return override
        _, env = self.resolve_env(relay_env)
        return env.base_url

    def get_deposit_address(self, relay_env: str | None = None) -> str:
        _, env = self.resolve_env(relay_env)
        deposit_address = env.deposit_address.strip()
        if not deposit_address:
            env_key, _ = self.resolve_env(relay_env)
            raise ValueError(
                f"MISSING_DEPOSIT_ADDRESS: relay deposit address is not configured for env '{env_key}'."
            )
        return deposit_address


def assert_relay_env_matches_network(relay_env: str, chain: ChainConfig) -> None:
    normalized_env = relay_env.strip().lower()
    expected_kind = RELAY_ENV_REQUIRED_NETWORK_KIND.get(normalized_env)
    if expected_kind is None:
        available = ", ".join(sorted(VALID_RELAY_ENVS))
        raise ValueError(
            f"INVALID_RELAY_ENV: '{normalized_env}' is not supported. Supported: {available}."
        )
    if chain.network_kind != expected_kind:
        raise ValueError(
            "INVALID_RELAY_NETWORK_PAIRING: "
            f"relay_env '{normalized_env}' requires network_kind '{expected_kind}', "
            f"but network '{chain.network_key}' has network_kind '{chain.network_kind}'."
        )


def load_relay_config() -> RelayConfig:
    data_path = files("crynux_mcp.config").joinpath("relay.json")
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    payload = _cast_dict(raw)

    default_env = str(payload.get("default_env", "")).strip().lower()
    if default_env not in VALID_RELAY_ENVS:
        raise ValueError(
            "INVALID_RELAY_CONFIG: default_env must be 'staging' or 'production'."
        )

    timeout_seconds = int(payload.get("timeout_seconds", 10))
    if timeout_seconds <= 0:
        raise ValueError("INVALID_RELAY_CONFIG: timeout_seconds must be greater than 0.")

    auth_safety_margin_seconds = int(payload.get("auth_safety_margin_seconds", 30))
    if auth_safety_margin_seconds < 0:
        raise ValueError("INVALID_RELAY_CONFIG: auth_safety_margin_seconds must be >= 0.")

    environments_raw = _cast_dict(payload.get("environments", {}))
    if not environments_raw:
        raise ValueError("INVALID_RELAY_CONFIG: environments must include at least one env.")

    environments: dict[str, RelayEnvironmentConfig] = {}
    for env_key, env_cfg in environments_raw.items():
        normalized_key = str(env_key).strip().lower()
        if normalized_key not in VALID_RELAY_ENVS:
            raise ValueError(
                f"INVALID_RELAY_CONFIG: environment '{normalized_key}' must be "
                f"'staging' or 'production'."
            )
        env_payload = _cast_dict(env_cfg)
        base_url = str(env_payload.get("base_url", "")).strip().rstrip("/")
        if not base_url:
            raise ValueError(f"INVALID_RELAY_CONFIG: environments.{normalized_key}.base_url is required.")
        deposit_address = str(env_payload.get("deposit_address", "")).strip()
        if not deposit_address:
            raise ValueError(
                f"INVALID_RELAY_CONFIG: environments.{normalized_key}.deposit_address is required."
            )
        environments[normalized_key] = RelayEnvironmentConfig(
            base_url=base_url,
            deposit_address=deposit_address,
        )

    if default_env not in environments:
        raise ValueError("INVALID_RELAY_CONFIG: default_env must exist in environments.")

    return RelayConfig(
        default_env=default_env,
        timeout_seconds=timeout_seconds,
        auth_safety_margin_seconds=auth_safety_margin_seconds,
        environments=environments,
    )


def _cast_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("INVALID_RELAY_CONFIG: expected object.")
    return value
