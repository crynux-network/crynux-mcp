from dataclasses import dataclass

from crynux_mcp.server import (
    handle_relay_deposit_initiate,
    handle_relay_deposit_latest_status,
    handle_relay_get_account_balance,
    handle_relay_get_auth_token,
    handle_relay_withdraw_create,
    handle_relay_withdraw_latest_status,
)
from crynux_mcp.relay.models import (
    RelayAuthTokenResult,
    RelayDepositListResult,
    RelayWithdrawCreateResult,
    RelayWithdrawListResult,
)


def test_handle_relay_get_auth_token_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crynux_mcp.server._resolve_network_key", lambda network: "dymension")
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False: RelayAuthTokenResult(
            token="jwt-abc",
            expires_at=1234567890,
            refreshed=bool(force_refresh),
        ),
    )

    payload = handle_relay_get_auth_token(
        network="dymension",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["token"] == "jwt-abc"
    assert payload["expires_at"] == 1234567890
    assert "network" not in payload
    assert "address" not in payload


def test_handle_relay_get_account_balance_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False: RelayAuthTokenResult(
            token="jwt-abc",
            expires_at=1234567890,
            refreshed=bool(force_refresh),
        ),
    )
    monkeypatch.setattr(
        "crynux_mcp.server.relay_client.get_account_balance",
        lambda address, token: "1000000000000000000",
    )

    payload = handle_relay_get_account_balance(
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["balance_wei"] == "1000000000000000000"
    assert "address" not in payload


def test_handle_relay_get_account_balance_accepts_key_name(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server.list_local_keys",
        lambda: [{"name": "my-key", "address": "0xA21036f5B1d15Dec5417Bcfb3Cd0Bd59e4f73Ee6", "is_default": True}],
    )
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False: RelayAuthTokenResult(
            token="jwt-abc",
            expires_at=1234567890,
            refreshed=bool(force_refresh),
        ),
    )
    monkeypatch.setattr(
        "crynux_mcp.server.relay_client.get_account_balance",
        lambda address, token: "1000000000000000000",
    )

    payload = handle_relay_get_account_balance(key_name="my-key")
    assert payload["balance_wei"] == "1000000000000000000"
    assert "address" not in payload


def test_handle_relay_withdraw_latest_status_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crynux_mcp.server._resolve_network_key", lambda network: "dymension")
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False: RelayAuthTokenResult(
            token="jwt-abc",
            expires_at=1234567890,
            refreshed=bool(force_refresh),
        ),
    )
    monkeypatch.setattr(
        "crynux_mcp.server.relay_client.list_withdraws",
        lambda address, page, page_size, token: RelayWithdrawListResult(
            page=page,
            page_size=page_size,
            total=2,
            withdraw_records=[
                {"id": 1, "created_at": 10, "status": 0},
                {"id": 2, "created_at": 20, "status": 1},
            ],
        ),
    )

    payload = handle_relay_withdraw_latest_status(
        network="dymension",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["kind"] == "withdraw"
    assert payload["status"] == "1"
    assert payload["latest_record"]["id"] == 2
    assert payload["found"] is True
    assert "network" not in payload
    assert "address" not in payload


def test_handle_relay_withdraw_create_uses_beneficial_address_when_set(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeChain:
        network_key = "dymension"

    @dataclass(frozen=True)
    class FakeBeneficialAddressResult:
        beneficial_address: str = "0x2222222222222222222222222222222222222222"
        is_set: bool = True

    captured: dict[str, str | int] = {}

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def get_beneficial_address(self, node_address: str):
            assert node_address == "0x1111111111111111111111111111111111111111"
            return FakeBeneficialAddressResult()

    monkeypatch.setattr("crynux_mcp.server.registry.resolve", lambda network: FakeChain())
    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False: RelayAuthTokenResult(
            token="jwt-abc",
            expires_at=1234567890,
            refreshed=bool(force_refresh),
        ),
    )

    def fake_sign_action(*, address: str, action: str, key_name=None):
        captured["signed_address"] = address
        captured["action"] = action
        _ = key_name
        return 1234567890, "0xsig"

    def fake_create_withdraw(*, address: str, amount: str, benefit_address: str, network: str, timestamp: int, signature: str, token: str):
        captured["create_address"] = address
        captured["amount"] = amount
        captured["benefit_address"] = benefit_address
        captured["network"] = network
        captured["timestamp"] = timestamp
        captured["signature"] = signature
        captured["token"] = token
        return RelayWithdrawCreateResult.create(
            amount_wei=amount,
            benefit_address=benefit_address,
            timestamp=timestamp,
            result={"id": 1},
        )

    monkeypatch.setattr("crynux_mcp.server.relay_auth.sign_action", fake_sign_action)
    monkeypatch.setattr("crynux_mcp.server.relay_client.create_withdraw", fake_create_withdraw)

    payload = handle_relay_withdraw_create(
        network="dymension",
        amount_wei="100",
        address="0x1111111111111111111111111111111111111111",
    )

    assert captured["benefit_address"] == "0x2222222222222222222222222222222222222222"
    assert (
        captured["action"]
        == "Withdraw 100 from 0x1111111111111111111111111111111111111111 to 0x2222222222222222222222222222222222222222 on dymension"
    )
    assert payload["benefit_address"] == "0x2222222222222222222222222222222222222222"
    assert payload["timestamp"] == 1234567890
    assert payload["result"] == {"id": 1}


def test_handle_relay_withdraw_create_falls_back_to_address_when_beneficial_not_set(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeChain:
        network_key = "dymension"

    @dataclass(frozen=True)
    class FakeBeneficialAddressResult:
        beneficial_address: str = "0x0000000000000000000000000000000000000000"
        is_set: bool = False

    captured: dict[str, str | int] = {}

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def get_beneficial_address(self, node_address: str):
            assert node_address == "0x1111111111111111111111111111111111111111"
            return FakeBeneficialAddressResult()

    monkeypatch.setattr("crynux_mcp.server.registry.resolve", lambda network: FakeChain())
    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False: RelayAuthTokenResult(
            token="jwt-abc",
            expires_at=1234567890,
            refreshed=bool(force_refresh),
        ),
    )

    def fake_sign_action(*, address: str, action: str, key_name=None):
        captured["signed_address"] = address
        captured["action"] = action
        _ = key_name
        return 1234567890, "0xsig"

    def fake_create_withdraw(*, address: str, amount: str, benefit_address: str, network: str, timestamp: int, signature: str, token: str):
        captured["create_address"] = address
        captured["amount"] = amount
        captured["benefit_address"] = benefit_address
        captured["network"] = network
        captured["timestamp"] = timestamp
        captured["signature"] = signature
        captured["token"] = token
        return RelayWithdrawCreateResult.create(
            amount_wei=amount,
            benefit_address=benefit_address,
            timestamp=timestamp,
            result={"id": 2},
        )

    monkeypatch.setattr("crynux_mcp.server.relay_auth.sign_action", fake_sign_action)
    monkeypatch.setattr("crynux_mcp.server.relay_client.create_withdraw", fake_create_withdraw)

    payload = handle_relay_withdraw_create(
        network="dymension",
        amount_wei="100",
        address="0x1111111111111111111111111111111111111111",
    )

    assert captured["benefit_address"] == "0x1111111111111111111111111111111111111111"
    assert (
        captured["action"]
        == "Withdraw 100 from 0x1111111111111111111111111111111111111111 to 0x1111111111111111111111111111111111111111 on dymension"
    )
    assert payload["benefit_address"] == "0x1111111111111111111111111111111111111111"
    assert payload["timestamp"] == 1234567890
    assert payload["result"] == {"id": 2}


def test_handle_relay_deposit_latest_status_empty(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crynux_mcp.server._resolve_network_key", lambda network: "dymension")
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False: RelayAuthTokenResult(
            token="jwt-abc",
            expires_at=1234567890,
            refreshed=bool(force_refresh),
        ),
    )
    monkeypatch.setattr(
        "crynux_mcp.server.relay_client.list_deposits",
        lambda address, page, page_size, token: RelayDepositListResult(
            page=page,
            page_size=page_size,
            total=0,
            deposit_records=[],
        ),
    )

    payload = handle_relay_deposit_latest_status(
        network="dymension",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["kind"] == "deposit"
    assert payload["found"] is False
    assert payload["latest_record"] == {}
    assert "network" not in payload
    assert "address" not in payload


def test_handle_relay_deposit_initiate_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeChain:
        network_key = "dymension"

    @dataclass(frozen=True)
    class FakeTransferResult:
        from_address: str = "0x1111111111111111111111111111111111111111"
        to: str = "0x2003D1F047C1948cfE12e449379e3ce487070765"
        value_wei: str = "100"
        tx_hash: str = "0xabc"

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
    assert payload["to"] == "0x2003D1F047C1948cfE12e449379e3ce487070765"
    assert payload["tx_hash"] == "0xabc"
    assert "deposit_address" not in payload
