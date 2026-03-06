from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP

from crynux_mcp.blockchain.evm_client import EvmClient
from crynux_mcp.config.loader import load_chain_registry
from crynux_mcp.relay.auth import RelayAuthManager
from crynux_mcp.relay.client import RelayApiClient, select_latest_record
from crynux_mcp.relay.config import load_relay_config
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
relay_config = load_relay_config()
relay_client = RelayApiClient(base_url=relay_config.base_url, timeout_seconds=relay_config.timeout_seconds)
relay_auth = RelayAuthManager(auth_safety_margin_seconds=relay_config.auth_safety_margin_seconds)


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


def handle_get_beneficial_address(network: str | None, node_address: str) -> dict[str, Any]:
    try:
        chain = registry.resolve(network)
        client = EvmClient(chain)
        result = client.get_beneficial_address(node_address=node_address)
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"network": network, "node_address": node_address}) from exc


def handle_set_beneficial_address(
    network: str | None,
    beneficial_address: str,
    key_name: str | None = None,
    gas_price_wei: int | None = None,
    gas_limit: int | None = None,
) -> dict[str, Any]:
    private_key: str | None = None
    try:
        private_key = get_private_key(name=key_name)
        chain = registry.resolve(network)
        client = EvmClient(chain)
        result = client.set_beneficial_address(
            private_key=private_key,
            beneficial_address=beneficial_address,
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
                "beneficial_address": beneficial_address,
                "gas_price_wei": gas_price_wei,
                "gas_limit": gas_limit,
            },
        ) from exc


def handle_get_node_staking_info(network: str | None, node_address: str) -> dict[str, Any]:
    try:
        chain = registry.resolve(network)
        client = EvmClient(chain)
        result = client.get_node_staking_info(node_address=node_address)
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"network": network, "node_address": node_address}) from exc


def handle_get_node_credits(network: str | None, node_address: str) -> dict[str, Any]:
    try:
        chain = registry.resolve(network)
        client = EvmClient(chain)
        result = client.get_node_credits(node_address=node_address)
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"network": network, "node_address": node_address}) from exc


def _resolve_network_key(network: str | None) -> str:
    chain = registry.resolve(network)
    return chain.network_key


def _get_relay_token(address: str, key_name: str | None = None, force_refresh: bool = False) -> dict[str, Any]:
    session = relay_auth.get_valid_session(
        address=address,
        key_name=key_name,
        api=relay_client,
        force_refresh=force_refresh,
    )
    return {"address": session.address, "token": session.token, "expires_at": session.expires_at}


def handle_relay_get_auth_token(
    network: str | None,
    address: str,
    key_name: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    try:
        network_key = _resolve_network_key(network)
        token_info = _get_relay_token(address=address, key_name=key_name, force_refresh=force_refresh)
        return _to_response_payload(
            {
                "network": network_key,
                "address": token_info["address"],
                "token": token_info["token"],
                "expires_at": token_info["expires_at"],
                "refreshed": bool(force_refresh),
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {"network": network, "address": address, "key_name": key_name, "force_refresh": force_refresh},
        ) from exc


def handle_relay_get_account_balance(
    network: str | None,
    address: str,
    key_name: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    try:
        network_key = _resolve_network_key(network)
        token_info = _get_relay_token(address=address, key_name=key_name)
        token = token_info["token"]
        balance_wei = relay_client.get_account_balance(address=address, token=token)
        return _to_response_payload(
            {
                "network": network_key,
                "address": token_info["address"],
                "balance_wei": balance_wei,
                "token_expires_at": token_info["expires_at"],
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"network": network, "address": address, "key_name": key_name, "token": token}) from exc


def handle_relay_withdraw_create(
    network: str | None,
    address: str,
    amount_wei: str,
    benefit_address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    signature: str | None = None
    try:
        network_key = _resolve_network_key(network)
        token_info = _get_relay_token(address=address, key_name=key_name)
        token = token_info["token"]
        destination = (benefit_address or address).strip()
        action = f"Withdraw {amount_wei} from {address} to {destination} on {network_key}"
        timestamp, signature = relay_auth.sign_action(
            address=address,
            action=action,
            key_name=key_name,
        )
        result = relay_client.create_withdraw(
            address=address,
            amount=amount_wei,
            benefit_address=destination,
            network=network_key,
            timestamp=timestamp,
            signature=signature,
            token=token,
        )
        return _to_response_payload(
            {
                "network": network_key,
                "address": address,
                "amount_wei": amount_wei,
                "benefit_address": destination,
                "timestamp": timestamp,
                "result": result,
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {
                "network": network,
                "address": address,
                "amount_wei": amount_wei,
                "benefit_address": benefit_address,
                "key_name": key_name,
                "token": token,
                "signature": signature,
            },
        ) from exc


def handle_relay_withdraw_list(
    network: str | None,
    address: str,
    page: int = 1,
    page_size: int = 10,
    key_name: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    try:
        network_key = _resolve_network_key(network)
        token_info = _get_relay_token(address=address, key_name=key_name)
        token = token_info["token"]
        result = relay_client.list_withdraws(address=address, page=page, page_size=page_size, token=token)
        return _to_response_payload(
            {
                "network": network_key,
                "address": address,
                "page": page,
                "page_size": page_size,
                "total": int(result.get("total", 0) or 0),
                "withdraw_records": result.get("withdraw_records", []),
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {"network": network, "address": address, "page": page, "page_size": page_size, "key_name": key_name, "token": token},
        ) from exc


def handle_relay_withdraw_latest_status(
    network: str | None,
    address: str,
    scan_page_size: int = 20,
    key_name: str | None = None,
) -> dict[str, Any]:
    try:
        payload = handle_relay_withdraw_list(
            network=network,
            address=address,
            page=1,
            page_size=scan_page_size,
            key_name=key_name,
        )
        records = payload.get("withdraw_records", [])
        if not isinstance(records, list):
            records = []
        latest = select_latest_record([item for item in records if isinstance(item, dict)])
        status = str(latest.get("status", "")) if latest else ""
        return _to_response_payload(
            {
                "network": payload.get("network"),
                "address": payload.get("address"),
                "kind": "withdraw",
                "status": status,
                "found": latest is not None,
                "latest_record": latest or {},
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {"network": network, "address": address, "scan_page_size": scan_page_size, "key_name": key_name},
        ) from exc


def handle_relay_deposit_list(
    network: str | None,
    address: str,
    page: int = 1,
    page_size: int = 10,
    key_name: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    try:
        network_key = _resolve_network_key(network)
        token_info = _get_relay_token(address=address, key_name=key_name)
        token = token_info["token"]
        result = relay_client.list_deposits(address=address, page=page, page_size=page_size, token=token)
        return _to_response_payload(
            {
                "network": network_key,
                "address": address,
                "page": page,
                "page_size": page_size,
                "total": int(result.get("total", 0) or 0),
                "deposit_records": result.get("deposit_records", []),
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {"network": network, "address": address, "page": page, "page_size": page_size, "key_name": key_name, "token": token},
        ) from exc


def handle_relay_deposit_latest_status(
    network: str | None,
    address: str,
    scan_page_size: int = 20,
    key_name: str | None = None,
) -> dict[str, Any]:
    try:
        payload = handle_relay_deposit_list(
            network=network,
            address=address,
            page=1,
            page_size=scan_page_size,
            key_name=key_name,
        )
        records = payload.get("deposit_records", [])
        if not isinstance(records, list):
            records = []
        latest = select_latest_record([item for item in records if isinstance(item, dict)])
        status = str(latest.get("status", "")) if latest else ""
        return _to_response_payload(
            {
                "network": payload.get("network"),
                "address": payload.get("address"),
                "kind": "deposit",
                "status": status,
                "found": latest is not None,
                "latest_record": latest or {},
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {"network": network, "address": address, "scan_page_size": scan_page_size, "key_name": key_name},
        ) from exc


def handle_relay_deposit_initiate(
    network: str | None,
    amount: str,
    key_name: str | None = None,
    unit: str | None = "ether",
    gas_price_wei: int | None = None,
    gas_limit: int | None = None,
) -> dict[str, Any]:
    private_key: str | None = None
    try:
        chain = registry.resolve(network)
        private_key = get_private_key(name=key_name)
        deposit_address = relay_config.get_deposit_address(chain.network_key)
        client = EvmClient(chain)
        transfer_result = client.transfer_native(
            private_key=private_key,
            to=deposit_address,
            amount=amount,
            unit=unit,
            gas_price_wei=gas_price_wei,
            gas_limit=gas_limit,
        )
        payload = _to_response_payload(transfer_result)
        payload["deposit_address"] = deposit_address
        payload["network"] = chain.network_key
        payload["text"] = json.dumps(payload, ensure_ascii=True)
        return payload
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {
                "network": network,
                "amount": amount,
                "key_name": key_name,
                "private_key": private_key,
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
def get_beneficial_address(network: str | None, node_address: str) -> dict[str, Any]:
    """Get beneficial address for an operational node wallet."""
    return handle_get_beneficial_address(network=network, node_address=node_address)


@mcp.tool()
def set_beneficial_address(
    network: str | None,
    beneficial_address: str,
    key_name: str | None = None,
    gas_price_wei: int | None = None,
    gas_limit: int | None = None,
) -> dict[str, Any]:
    """Set beneficial address using a named key or default local key."""
    return handle_set_beneficial_address(
        network=network,
        beneficial_address=beneficial_address,
        key_name=key_name,
        gas_price_wei=gas_price_wei,
        gas_limit=gas_limit,
    )


@mcp.tool()
def get_node_staking_info(network: str | None, node_address: str) -> dict[str, Any]:
    """Get staking information for a node wallet address."""
    return handle_get_node_staking_info(network=network, node_address=node_address)


@mcp.tool()
def get_node_credits(network: str | None, node_address: str) -> dict[str, Any]:
    """Get node credits balance for a node wallet address."""
    return handle_get_node_credits(network=network, node_address=node_address)


@mcp.tool()
def relay_get_account_balance(
    network: str | None,
    address: str,
    key_name: str | None = None,
) -> dict[str, Any]:
    """Get Relay account balance in wei for an EVM address."""
    return handle_relay_get_account_balance(network=network, address=address, key_name=key_name)


@mcp.tool()
def relay_withdraw_create(
    network: str | None,
    address: str,
    amount_wei: str,
    benefit_address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    """Create a Relay withdraw request signed by the local key."""
    return handle_relay_withdraw_create(
        network=network,
        address=address,
        amount_wei=amount_wei,
        benefit_address=benefit_address,
        key_name=key_name,
    )


@mcp.tool()
def relay_withdraw_list(
    network: str | None,
    address: str,
    page: int = 1,
    page_size: int = 10,
    key_name: str | None = None,
) -> dict[str, Any]:
    """List Relay withdraw requests for an address."""
    return handle_relay_withdraw_list(
        network=network,
        address=address,
        page=page,
        page_size=page_size,
        key_name=key_name,
    )


@mcp.tool()
def relay_withdraw_latest_status(
    network: str | None,
    address: str,
    scan_page_size: int = 20,
    key_name: str | None = None,
) -> dict[str, Any]:
    """Get latest status from Relay withdraw records."""
    return handle_relay_withdraw_latest_status(
        network=network,
        address=address,
        scan_page_size=scan_page_size,
        key_name=key_name,
    )


@mcp.tool()
def relay_deposit_initiate(
    network: str | None,
    amount: str,
    key_name: str | None = None,
    unit: str | None = "ether",
    gas_price_wei: int | None = None,
    gas_limit: int | None = None,
) -> dict[str, Any]:
    """Initiate Relay deposit by sending on-chain CNX to Relay deposit address."""
    return handle_relay_deposit_initiate(
        network=network,
        amount=amount,
        key_name=key_name,
        unit=unit,
        gas_price_wei=gas_price_wei,
        gas_limit=gas_limit,
    )


@mcp.tool()
def relay_deposit_list(
    network: str | None,
    address: str,
    page: int = 1,
    page_size: int = 10,
    key_name: str | None = None,
) -> dict[str, Any]:
    """List Relay deposit records for an address."""
    return handle_relay_deposit_list(
        network=network,
        address=address,
        page=page,
        page_size=page_size,
        key_name=key_name,
    )


@mcp.tool()
def relay_deposit_latest_status(
    network: str | None,
    address: str,
    scan_page_size: int = 20,
    key_name: str | None = None,
) -> dict[str, Any]:
    """Get latest status from Relay deposit records."""
    return handle_relay_deposit_latest_status(
        network=network,
        address=address,
        scan_page_size=scan_page_size,
        key_name=key_name,
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
