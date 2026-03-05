from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP

from crynux_mcp.blockchain.evm_client import EvmClient
from crynux_mcp.config.loader import load_chain_registry
from crynux_mcp.security.key_store import (
    create_key as create_local_key,
    delete_key as delete_local_key,
    export_key as export_local_key,
    get_private_key,
    list_keys as list_local_keys,
    set_default_key as set_default_local_key,
)
from crynux_mcp.security.redaction import redact_secrets, sanitize_error_message

mcp = FastMCP("crynux-mcp")
registry = load_chain_registry()


def _to_response_payload(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        payload = asdict(value)
    elif isinstance(value, dict):
        payload = value
    else:
        payload = {"value": value}
    payload["text"] = json.dumps(payload, ensure_ascii=True)
    return payload


def _execution_error(exc: Exception, args: dict[str, Any] | None = None) -> RuntimeError:
    _ = redact_secrets(args or {})
    message = sanitize_error_message(str(exc))
    return RuntimeError(message)


def handle_get_balance(network: str | None, address: str, unit: str | None = None) -> dict[str, Any]:
    try:
        chain = registry.resolve(network)
        client = EvmClient(chain)
        result = client.get_balance(address=address, unit=unit)
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"network": network, "address": address, "unit": unit}) from exc


def handle_transfer_native(
    network: str | None,
    to: str,
    amount: str,
    key_name: str | None = None,
    unit: str | None = "ether",
    gas_price_wei: int | None = None,
    gas_limit: int | None = None,
) -> dict[str, Any]:
    private_key: str | None = None
    try:
        private_key = get_private_key(name=key_name)
        chain = registry.resolve(network)
        client = EvmClient(chain)
        result = client.transfer_native(
            private_key=private_key,
            to=to,
            amount=amount,
            unit=unit,
            gas_price_wei=gas_price_wei,
            gas_limit=gas_limit,
        )
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {
                "network": network,
                "key_name": key_name,
                "private_key": private_key,
                "to": to,
                "amount": amount,
                "unit": unit,
                "gas_price_wei": gas_price_wei,
                "gas_limit": gas_limit,
            },
        ) from exc


@mcp.tool()
def get_balance(network: str | None, address: str, unit: str | None = None) -> dict[str, Any]:
    """Get native CNX balance on a selected Crynux EVM network."""
    return handle_get_balance(network=network, address=address, unit=unit)


@mcp.tool()
def transfer_native(
    network: str | None,
    to: str,
    amount: str,
    key_name: str | None = None,
    unit: str | None = "ether",
    gas_price_wei: int | None = None,
    gas_limit: int | None = None,
) -> dict[str, Any]:
    """Transfer native CNX using a named key or default local key."""
    return handle_transfer_native(
        network=network,
        to=to,
        amount=amount,
        key_name=key_name,
        unit=unit,
        gas_price_wei=gas_price_wei,
        gas_limit=gas_limit,
    )


@mcp.tool()
def create_key(name: str) -> dict[str, Any]:
    """Create a new local signer key with the provided name."""
    try:
        result = create_local_key(name=name)
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"name": name}) from exc


@mcp.tool()
def list_keys() -> dict[str, Any]:
    """List local signer key names and addresses."""
    try:
        keys = list_local_keys()
        return _to_response_payload({"keys": keys, "count": len(keys)})
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc) from exc


@mcp.tool()
def delete_key(name: str) -> dict[str, Any]:
    """Delete a local signer key by name."""
    try:
        delete_local_key(name=name)
        return _to_response_payload({"name": name, "deleted": True})
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"name": name}) from exc


@mcp.tool()
def set_default_key(name: str) -> dict[str, Any]:
    """Set the default local signer key by name."""
    try:
        result = set_default_local_key(name=name)
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"name": name}) from exc


@mcp.tool()
def export_key(name: str, filename: str) -> dict[str, Any]:
    """Export a named local signer key to a file path."""
    try:
        result = export_local_key(name=name, filename=filename)
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"name": name, "filename": filename}) from exc


def run() -> None:
    mcp.run(transport="stdio")
