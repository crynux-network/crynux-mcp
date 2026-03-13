from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP

from crynux_mcp.blockchain.evm_client import EvmClient
from crynux_mcp.config.loader import load_chain_registry
from crynux_mcp.relay.auth import RelayAuthManager
from crynux_mcp.relay.client import RelayApiClient
from crynux_mcp.relay.config import load_relay_config
from crynux_mcp.relay.models import (
    RelayAccountBalanceResult,
    RelayAuthTokenResult,
    RelayLatestStatusResult,
)
from crynux_mcp.security.key_store import (
    create_key as create_local_key,
    delete_key as delete_local_key,
    export_key as export_local_key,
    get_private_key,
    list_keys as list_local_keys,
    set_default_key as set_default_local_key,
)
from crynux_mcp.security.redaction import redact_secrets, sanitize_error_message
from crynux_mcp.security.schemas import KeyDeleteResult, KeyListResult

mcp = FastMCP("crynux-mcp")
registry = load_chain_registry()
relay_config = load_relay_config()
relay_client = RelayApiClient(base_url=relay_config.base_url, timeout_seconds=relay_config.timeout_seconds)
relay_auth = RelayAuthManager(auth_safety_margin_seconds=relay_config.auth_safety_margin_seconds)
_relay_clients: dict[str, RelayApiClient] = {}
_relay_auth_managers: dict[str, RelayAuthManager] = {}


def _to_response_payload(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        payload = asdict(value)
    elif isinstance(value, dict):
        payload = dict(value)
    else:
        payload = {"value": value}
    return payload


def _execution_error(exc: Exception, args: dict[str, Any] | None = None) -> RuntimeError:
    _ = redact_secrets(args or {})
    message = sanitize_error_message(str(exc))
    return RuntimeError(message)


def _address_from_key_name(key_name: str) -> str:
    normalized = (key_name or "").strip()
    if not normalized:
        raise ValueError("INVALID_KEY_NAME: key name is required.")
    for key in list_local_keys():
        if key.get("name") == normalized:
            address = str(key.get("address") or "").strip()
            if address:
                return address
            break
    raise ValueError(f"KEY_NOT_FOUND: key '{normalized}' does not exist.")


def _resolve_address(address: str | None = None, key_name: str | None = None) -> str:
    if key_name is not None:
        return _address_from_key_name(key_name)
    resolved = (address or "").strip()
    if resolved:
        return resolved
    raise ValueError("INVALID_ADDRESS: provide either 'address' or 'key_name'.")


def handle_get_balance(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    try:
        chain = registry.resolve(network)
        client = EvmClient(chain)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        return _to_response_payload(client.get_balance(address=resolved_address))
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"network": network, "address": address, "key_name": key_name}) from exc


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


def handle_get_beneficial_address(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    try:
        chain = registry.resolve(network)
        client = EvmClient(chain)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        return _to_response_payload(client.get_beneficial_address(node_address=resolved_address))
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"network": network, "address": address, "key_name": key_name}) from exc


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


def handle_get_node_staking_info(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    try:
        chain = registry.resolve(network)
        client = EvmClient(chain)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        return _to_response_payload(client.get_node_staking_info(node_address=resolved_address))
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"network": network, "address": address, "key_name": key_name}) from exc


def handle_get_node_credits(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    try:
        chain = registry.resolve(network)
        client = EvmClient(chain)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        return _to_response_payload(client.get_node_credits(node_address=resolved_address))
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc, {"network": network, "address": address, "key_name": key_name}) from exc


def _resolve_network_key(network: str | None) -> str:
    chain = registry.resolve(network)
    return chain.network_key


def _resolve_relay_withdraw_destination(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
) -> tuple[str, str, str]:
    chain = registry.resolve(network)
    client = EvmClient(chain)
    resolved_address = _resolve_address(address=address, key_name=key_name)
    beneficial_result = client.get_beneficial_address(node_address=resolved_address)
    destination = beneficial_result.beneficial_address if beneficial_result.is_set else resolved_address
    return chain.network_key, resolved_address, destination


def _relay_token_service_name(base_url: str) -> str:
    digest = hashlib.sha256(base_url.encode("utf-8")).hexdigest()[:16]
    return f"crynux-mcp-relay:{digest}"


def _resolve_relay_context(relay_base_url: str | None = None) -> tuple[RelayApiClient, RelayAuthManager]:
    normalized = (relay_base_url or "").strip().rstrip("/")
    if not normalized or normalized == relay_config.base_url:
        return relay_client, relay_auth

    cached_client = _relay_clients.get(normalized)
    cached_auth = _relay_auth_managers.get(normalized)
    if cached_client is not None and cached_auth is not None:
        return cached_client, cached_auth

    client = RelayApiClient(base_url=normalized, timeout_seconds=relay_config.timeout_seconds)
    auth_manager = RelayAuthManager(
        auth_safety_margin_seconds=relay_config.auth_safety_margin_seconds,
        token_service_name=_relay_token_service_name(normalized),
    )
    _relay_clients[normalized] = client
    _relay_auth_managers[normalized] = auth_manager
    return client, auth_manager


def _get_relay_token(
    address: str,
    key_name: str | None = None,
    force_refresh: bool = False,
    relay_api: RelayApiClient | None = None,
    relay_auth_manager: RelayAuthManager | None = None,
) -> RelayAuthTokenResult:
    api = relay_api or relay_client
    auth_manager = relay_auth_manager or relay_auth
    session = auth_manager.get_valid_session(
        address=address,
        key_name=key_name,
        api=api,
        force_refresh=force_refresh,
    )
    return RelayAuthTokenResult.from_session(session, refreshed=bool(force_refresh))


def handle_relay_get_auth_token(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    try:
        _ = _resolve_network_key(network)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        token_info = _get_relay_token(address=resolved_address, key_name=key_name, force_refresh=force_refresh)
        return _to_response_payload(token_info)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {"network": network, "address": address, "key_name": key_name, "force_refresh": force_refresh},
        ) from exc


def handle_relay_get_account_balance(
    address: str | None = None,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    try:
        relay_api, relay_auth_manager = _resolve_relay_context(relay_base_url)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        token_info = _get_relay_token(
            address=resolved_address,
            key_name=key_name,
            relay_api=relay_api,
            relay_auth_manager=relay_auth_manager,
        )
        token = token_info.token
        balance_wei = relay_api.get_account_balance(address=resolved_address, token=token)
        return _to_response_payload(RelayAccountBalanceResult.create(balance_wei=balance_wei))
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {"address": address, "key_name": key_name, "relay_base_url": relay_base_url, "token": token},
        ) from exc


def handle_relay_withdraw_create(
    network: str | None,
    amount_wei: str,
    address: str | None = None,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    signature: str | None = None
    try:
        relay_api, relay_auth_manager = _resolve_relay_context(relay_base_url)
        network_key, resolved_address, destination = _resolve_relay_withdraw_destination(
            network=network,
            address=address,
            key_name=key_name,
        )
        token_info = _get_relay_token(
            address=resolved_address,
            key_name=key_name,
            relay_api=relay_api,
            relay_auth_manager=relay_auth_manager,
        )
        token = token_info.token
        action = f"Withdraw {amount_wei} from {resolved_address} to {destination} on {network_key}"
        timestamp, signature = relay_auth.sign_action(
            address=resolved_address,
            action=action,
            key_name=key_name,
        )
        result = relay_api.create_withdraw(
            address=resolved_address,
            amount=amount_wei,
            benefit_address=destination,
            network=network_key,
            timestamp=timestamp,
            signature=signature,
            token=token,
        )
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {
                "network": network,
                "address": address,
                "amount_wei": amount_wei,
                "key_name": key_name,
                "relay_base_url": relay_base_url,
                "token": token,
                "signature": signature,
            },
        ) from exc


def handle_relay_withdraw_list(
    address: str | None = None,
    page: int = 1,
    page_size: int = 10,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    try:
        relay_api, relay_auth_manager = _resolve_relay_context(relay_base_url)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        token_info = _get_relay_token(
            address=resolved_address,
            key_name=key_name,
            relay_api=relay_api,
            relay_auth_manager=relay_auth_manager,
        )
        token = token_info.token
        result = relay_api.list_withdraws(address=resolved_address, page=page, page_size=page_size, token=token)
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {
                "address": address,
                "page": page,
                "page_size": page_size,
                "key_name": key_name,
                "relay_base_url": relay_base_url,
                "token": token,
            },
        ) from exc


def handle_relay_withdraw_latest_status(
    network: str | None,
    address: str | None = None,
    scan_page_size: int = 20,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    try:
        relay_api, relay_auth_manager = _resolve_relay_context(relay_base_url)
        _ = _resolve_network_key(network)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        token_info = _get_relay_token(
            address=resolved_address,
            key_name=key_name,
            relay_api=relay_api,
            relay_auth_manager=relay_auth_manager,
        )
        token = token_info.token
        result = relay_api.list_withdraws(address=resolved_address, page=1, page_size=scan_page_size, token=token)
        records = result.withdraw_records
        return _to_response_payload(RelayLatestStatusResult.from_records(kind="withdraw", records=records))
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {
                "network": network,
                "address": address,
                "scan_page_size": scan_page_size,
                "key_name": key_name,
                "relay_base_url": relay_base_url,
                "token": token,
            },
        ) from exc


def handle_relay_deposit_list(
    address: str | None = None,
    page: int = 1,
    page_size: int = 10,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    try:
        relay_api, relay_auth_manager = _resolve_relay_context(relay_base_url)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        token_info = _get_relay_token(
            address=resolved_address,
            key_name=key_name,
            relay_api=relay_api,
            relay_auth_manager=relay_auth_manager,
        )
        token = token_info.token
        result = relay_api.list_deposits(address=resolved_address, page=page, page_size=page_size, token=token)
        return _to_response_payload(result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {
                "address": address,
                "page": page,
                "page_size": page_size,
                "key_name": key_name,
                "relay_base_url": relay_base_url,
                "token": token,
            },
        ) from exc


def handle_relay_deposit_latest_status(
    network: str | None,
    address: str | None = None,
    scan_page_size: int = 20,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    token: str | None = None
    try:
        relay_api, relay_auth_manager = _resolve_relay_context(relay_base_url)
        _ = _resolve_network_key(network)
        resolved_address = _resolve_address(address=address, key_name=key_name)
        token_info = _get_relay_token(
            address=resolved_address,
            key_name=key_name,
            relay_api=relay_api,
            relay_auth_manager=relay_auth_manager,
        )
        token = token_info.token
        result = relay_api.list_deposits(address=resolved_address, page=1, page_size=scan_page_size, token=token)
        records = result.deposit_records
        return _to_response_payload(RelayLatestStatusResult.from_records(kind="deposit", records=records))
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {
                "network": network,
                "address": address,
                "scan_page_size": scan_page_size,
                "key_name": key_name,
                "relay_base_url": relay_base_url,
                "token": token,
            },
        ) from exc


def handle_relay_deposit_initiate(
    network: str | None,
    amount: str,
    key_name: str | None = None,
    unit: str | None = "ether",
    gas_price_wei: int | None = None,
    gas_limit: int | None = None,
    relay_base_url: str | None = None,
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
        return _to_response_payload(transfer_result)
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(
            exc,
            {
                "network": network,
                "amount": amount,
                "key_name": key_name,
                "private_key": private_key,
                "relay_base_url": relay_base_url,
                "unit": unit,
                "gas_price_wei": gas_price_wei,
                "gas_limit": gas_limit,
            },
        ) from exc


@mcp.tool()
def get_balance(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    """Get native CNX balance on a selected Crynux EVM network."""
    return handle_get_balance(network=network, address=address, key_name=key_name)


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
def get_beneficial_address(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    """Get beneficial address for an operational node wallet."""
    return handle_get_beneficial_address(network=network, address=address, key_name=key_name)


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
def get_node_staking_info(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    """Get staking information for a node wallet address."""
    return handle_get_node_staking_info(network=network, address=address, key_name=key_name)


@mcp.tool()
def get_node_credits(
    network: str | None,
    address: str | None = None,
    key_name: str | None = None,
) -> dict[str, Any]:
    """Get node credits balance for a node wallet address."""
    return handle_get_node_credits(network=network, address=address, key_name=key_name)


@mcp.tool()
def relay_get_account_balance(
    address: str | None = None,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    """Get Relay account balance in wei for an EVM address."""
    return handle_relay_get_account_balance(address=address, key_name=key_name, relay_base_url=relay_base_url)


@mcp.tool()
def relay_withdraw_create(
    network: str | None,
    amount_wei: str,
    address: str | None = None,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    """Create a Relay withdraw request signed by the local key."""
    return handle_relay_withdraw_create(
        network=network,
        address=address,
        amount_wei=amount_wei,
        key_name=key_name,
        relay_base_url=relay_base_url,
    )


@mcp.tool()
def relay_withdraw_list(
    address: str | None = None,
    page: int = 1,
    page_size: int = 10,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    """List Relay withdraw requests for an address."""
    return handle_relay_withdraw_list(
        address=address,
        page=page,
        page_size=page_size,
        key_name=key_name,
        relay_base_url=relay_base_url,
    )


@mcp.tool()
def relay_withdraw_latest_status(
    network: str | None,
    address: str | None = None,
    scan_page_size: int = 20,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    """Get latest status from Relay withdraw records (0=Processing, 1=Success, 2=Failed)."""
    return handle_relay_withdraw_latest_status(
        network=network,
        address=address,
        scan_page_size=scan_page_size,
        key_name=key_name,
        relay_base_url=relay_base_url,
    )


@mcp.tool()
def relay_deposit_initiate(
    network: str | None,
    amount: str,
    key_name: str | None = None,
    unit: str | None = "ether",
    gas_price_wei: int | None = None,
    gas_limit: int | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    """Initiate Relay deposit by sending on-chain CNX to Relay deposit address."""
    return handle_relay_deposit_initiate(
        network=network,
        amount=amount,
        key_name=key_name,
        unit=unit,
        gas_price_wei=gas_price_wei,
        gas_limit=gas_limit,
        relay_base_url=relay_base_url,
    )


@mcp.tool()
def relay_deposit_list(
    address: str | None = None,
    page: int = 1,
    page_size: int = 10,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    """List Relay deposit records for an address."""
    return handle_relay_deposit_list(
        address=address,
        page=page,
        page_size=page_size,
        key_name=key_name,
        relay_base_url=relay_base_url,
    )


@mcp.tool()
def relay_deposit_latest_status(
    network: str | None,
    address: str | None = None,
    scan_page_size: int = 20,
    key_name: str | None = None,
    relay_base_url: str | None = None,
) -> dict[str, Any]:
    """Get latest status from Relay deposit records (0=Processing, 1=Success, 2=Failed)."""
    return handle_relay_deposit_latest_status(
        network=network,
        address=address,
        scan_page_size=scan_page_size,
        key_name=key_name,
        relay_base_url=relay_base_url,
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
        return _to_response_payload(KeyListResult.from_keys(keys))
    except Exception as exc:  # noqa: BLE001
        raise _execution_error(exc) from exc


@mcp.tool()
def delete_key(name: str) -> dict[str, Any]:
    """Delete a local signer key by name."""
    try:
        delete_local_key(name=name)
        return _to_response_payload(KeyDeleteResult.from_name(name))
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
