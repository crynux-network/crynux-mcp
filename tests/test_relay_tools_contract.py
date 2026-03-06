from dataclasses import dataclass

from crynux_mcp.server import (
    handle_relay_deposit_initiate,
    handle_relay_deposit_latest_status,
    handle_relay_get_account_balance,
    handle_relay_get_auth_token,
    handle_relay_withdraw_latest_status,
)


def test_handle_relay_get_auth_token_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crynux_mcp.server._resolve_network_key", lambda network: "dymension")
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False: {
            "address": address.lower(),
            "token": "jwt-abc",
            "expires_at": 1234567890,
        },
    )

    payload = handle_relay_get_auth_token(
        network="dymension",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["network"] == "dymension"
    assert payload["token"] == "jwt-abc"
    assert payload["expires_at"] == 1234567890
    assert "text" in payload


def test_handle_relay_get_account_balance_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crynux_mcp.server._resolve_network_key", lambda network: "dymension")
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False: {
            "address": address.lower(),
            "token": "jwt-abc",
            "expires_at": 1234567890,
        },
    )
    monkeypatch.setattr(
        "crynux_mcp.server.relay_client.get_account_balance",
        lambda address, token: "1000000000000000000",
    )

    payload = handle_relay_get_account_balance(
        network="dymension",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["network"] == "dymension"
    assert payload["balance_wei"] == "1000000000000000000"
    assert "text" in payload


def test_handle_relay_withdraw_latest_status_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server.handle_relay_withdraw_list",
        lambda **kwargs: {
            "network": "dymension",
            "address": kwargs["address"],
            "withdraw_records": [
                {"id": 1, "created_at": 10, "status": 0},
                {"id": 2, "created_at": 20, "status": 1},
            ],
            "text": "{}",
        },
    )

    payload = handle_relay_withdraw_latest_status(
        network="dymension",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["kind"] == "withdraw"
    assert payload["status"] == "1"
    assert payload["latest_record"]["id"] == 2
    assert payload["found"] is True
    assert "text" in payload


def test_handle_relay_deposit_latest_status_empty(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server.handle_relay_deposit_list",
        lambda **kwargs: {
            "network": "dymension",
            "address": kwargs["address"],
            "deposit_records": [],
            "text": "{}",
        },
    )

    payload = handle_relay_deposit_latest_status(
        network="dymension",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["kind"] == "deposit"
    assert payload["found"] is False
    assert payload["latest_record"] == {}
    assert "text" in payload


def test_handle_relay_deposit_initiate_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeChain:
        network_key = "dymension"

    @dataclass(frozen=True)
    class FakeTransferResult:
        network: str = "dymension"
        from_address: str = "0x1111111111111111111111111111111111111111"
        to: str = "0x2003D1F047C1948cfE12e449379e3ce487070765"
        value_wei: str = "100"
        tx_hash: str = "0xabc"
        chain_id: int = 1313161573

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def transfer_native(self, **_kwargs):
            return FakeTransferResult()

    class FakeRelayConfig:
        def get_deposit_address(self, network: str) -> str:
            _ = network
            return "0x2003D1F047C1948cfE12e449379e3ce487070765"

    monkeypatch.setattr("crynux_mcp.server.registry.resolve", lambda network: FakeChain())
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: "0xabc")
    monkeypatch.setattr("crynux_mcp.server.relay_config", FakeRelayConfig())
    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)

    payload = handle_relay_deposit_initiate(network="dymension", amount="1")
    assert payload["network"] == "dymension"
    assert payload["deposit_address"] == "0x2003D1F047C1948cfE12e449379e3ce487070765"
    assert payload["tx_hash"] == "0xabc"
    assert "text" in payload
