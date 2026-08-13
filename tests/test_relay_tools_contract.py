from dataclasses import dataclass

from crynux_mcp.config.loader import ChainConfig, NativeCurrency
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


def _mainnet_chain(network_key: str = "crynux-on-base") -> ChainConfig:
    return ChainConfig(
        network_key=network_key,
        network_kind="mainnet",
        chain_id=18896214,
        chain_name="Crynux on Base",
        rpc_url="https://json-rpc.base.crynux.io",
        native_currency=NativeCurrency(name="Crynux", symbol="CNX", decimals=18),
        contracts={},
    )


def _testnet_chain(network_key: str = "crynux-on-base-sepolia") -> ChainConfig:
    return ChainConfig(
        network_key=network_key,
        network_kind="testnet",
        chain_id=188962142,
        chain_name="Crynux on Base Sepolia",
        rpc_url="https://json-rpc.base-sepolia.crynux.io",
        native_currency=NativeCurrency(name="Crynux", symbol="CNX", decimals=18),
        contracts={},
    )


def test_handle_relay_get_auth_token_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crynux_mcp.server._resolve_network_key", lambda network: "crynux-on-base")
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False, **_kwargs: RelayAuthTokenResult(
            token="jwt-abc",
            expires_at=1234567890,
            refreshed=bool(force_refresh),
        ),
    )

    payload = handle_relay_get_auth_token(
        network="crynux-on-base",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["token"] == "jwt-abc"
    assert payload["expires_at"] == 1234567890
    assert "network" not in payload
    assert "address" not in payload


def test_handle_relay_get_account_balance_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False, **_kwargs: RelayAuthTokenResult(
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
        lambda address, key_name=None, force_refresh=False, **_kwargs: RelayAuthTokenResult(
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


def test_handle_relay_get_account_balance_uses_custom_relay_base_url(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    class FakeRelayApi:
        def get_account_balance(self, *, address: str, token: str) -> str:
            captured["balance_address"] = address
            captured["balance_token"] = token
            return "42"

    class FakeRelayAuth:
        pass

    def fake_resolve_relay_context(relay_env: str | None = None, relay_base_url: str | None = None):
        captured["relay_env"] = relay_env
        captured["relay_base_url"] = relay_base_url
        return "staging", FakeRelayApi(), FakeRelayAuth()

    def fake_get_relay_token(*, address: str, key_name=None, force_refresh=False, relay_api=None, relay_auth_manager=None):
        captured["token_address"] = address
        captured["token_key_name"] = key_name
        captured["token_force_refresh"] = force_refresh
        captured["token_relay_api"] = relay_api is not None
        captured["token_relay_auth"] = relay_auth_manager is not None
        return RelayAuthTokenResult(token="jwt-custom", expires_at=1234567890, refreshed=False)

    monkeypatch.setattr("crynux_mcp.server._resolve_relay_context", fake_resolve_relay_context)
    monkeypatch.setattr("crynux_mcp.server._get_relay_token", fake_get_relay_token)

    payload = handle_relay_get_account_balance(
        address="0x1111111111111111111111111111111111111111",
        relay_env="staging",
        relay_base_url="https://relay.custom.test",
    )
    assert payload["balance_wei"] == "42"
    assert captured["relay_env"] == "staging"
    assert captured["relay_base_url"] == "https://relay.custom.test"
    assert captured["token_relay_api"] is True
    assert captured["token_relay_auth"] is True
    assert captured["balance_token"] == "jwt-custom"


def test_handle_relay_withdraw_latest_status_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server._resolve_relay_env_and_chain",
        lambda network, relay_env=None: ("production", _mainnet_chain()),
    )
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False, **_kwargs: RelayAuthTokenResult(
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
        network="crynux-on-base",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["kind"] == "withdraw"
    assert payload["status"] == "1"
    assert payload["latest_record"]["id"] == 2
    assert payload["found"] is True
    assert "network" not in payload
    assert "address" not in payload


def test_handle_relay_withdraw_create_uses_beneficial_address_when_set(monkeypatch) -> None:  # type: ignore[no-untyped-def]
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

    monkeypatch.setattr(
        "crynux_mcp.server._resolve_relay_env_and_chain",
        lambda network, relay_env=None: ("production", _mainnet_chain()),
    )
    monkeypatch.setattr("crynux_mcp.server.registry.resolve", lambda network: _mainnet_chain())
    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False, **_kwargs: RelayAuthTokenResult(
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
        network="crynux-on-base",
        amount_wei="100",
        address="0x1111111111111111111111111111111111111111",
    )

    assert captured["benefit_address"] == "0x2222222222222222222222222222222222222222"
    assert (
        captured["action"]
        == "Withdraw 100 from 0x1111111111111111111111111111111111111111 to 0x2222222222222222222222222222222222222222 on crynux-on-base"
    )
    assert payload["benefit_address"] == "0x2222222222222222222222222222222222222222"
    assert payload["timestamp"] == 1234567890
    assert payload["result"] == {"id": 1}


def test_handle_relay_withdraw_create_falls_back_to_address_when_beneficial_not_set(monkeypatch) -> None:  # type: ignore[no-untyped-def]
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

    monkeypatch.setattr(
        "crynux_mcp.server._resolve_relay_env_and_chain",
        lambda network, relay_env=None: ("production", _mainnet_chain()),
    )
    monkeypatch.setattr("crynux_mcp.server.registry.resolve", lambda network: _mainnet_chain())
    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False, **_kwargs: RelayAuthTokenResult(
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
        network="crynux-on-base",
        amount_wei="100",
        address="0x1111111111111111111111111111111111111111",
    )

    assert captured["benefit_address"] == "0x1111111111111111111111111111111111111111"
    assert (
        captured["action"]
        == "Withdraw 100 from 0x1111111111111111111111111111111111111111 to 0x1111111111111111111111111111111111111111 on crynux-on-base"
    )
    assert payload["benefit_address"] == "0x1111111111111111111111111111111111111111"
    assert payload["timestamp"] == 1234567890
    assert payload["result"] == {"id": 2}


def test_handle_relay_deposit_latest_status_empty(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server._resolve_relay_env_and_chain",
        lambda network, relay_env=None: ("production", _mainnet_chain()),
    )
    monkeypatch.setattr(
        "crynux_mcp.server._get_relay_token",
        lambda address, key_name=None, force_refresh=False, **_kwargs: RelayAuthTokenResult(
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
        network="crynux-on-base",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["kind"] == "deposit"
    assert payload["found"] is False
    assert payload["latest_record"] == {}
    assert "network" not in payload
    assert "address" not in payload


def test_handle_relay_deposit_initiate_uses_deposit_address_from_relay_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    @dataclass(frozen=True)
    class FakeTransferResult:
        from_address: str = "0x1111111111111111111111111111111111111111"
        to: str = "0x7bB0A0582893c09ED48397BFACDdbbd478eB4839"
        value_wei: str = "100"
        tx_hash: str = "0xabc"

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def transfer_native(self, **kwargs):
            captured["to"] = kwargs["to"]
            return FakeTransferResult()

    class FakeRelayConfig:
        def resolve_env(self, relay_env=None):
            selected = (relay_env or "staging").strip().lower()
            return selected, object()

        def get_deposit_address(self, relay_env=None):
            captured["deposit_env"] = relay_env
            return "0x7bB0A0582893c09ED48397BFACDdbbd478eB4839"

    monkeypatch.setattr(
        "crynux_mcp.server._resolve_relay_env_and_chain",
        lambda network, relay_env=None: ("staging", _testnet_chain()),
    )
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: "0xabc")
    monkeypatch.setattr("crynux_mcp.server.relay_config", FakeRelayConfig())
    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)

    payload = handle_relay_deposit_initiate(
        network="crynux-on-base-sepolia",
        amount="1",
        relay_env="staging",
    )
    assert captured["deposit_env"] == "staging"
    assert captured["to"] == "0x7bB0A0582893c09ED48397BFACDdbbd478eB4839"
    assert payload["to"] == "0x7bB0A0582893c09ED48397BFACDdbbd478eB4839"
    assert payload["tx_hash"] == "0xabc"
    assert "deposit_address" not in payload


def test_handle_relay_deposit_initiate_rejects_mismatched_env_network(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeRegistry:
        def resolve(self, network):
            _ = network
            return _mainnet_chain()

    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())

    try:
        handle_relay_deposit_initiate(
            network="crynux-on-base",
            amount="1",
            relay_env="staging",
        )
    except RuntimeError as exc:
        assert "INVALID_RELAY_NETWORK_PAIRING" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_handle_relay_withdraw_create_rejects_mismatched_env_network(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeRegistry:
        def resolve(self, network):
            _ = network
            return _testnet_chain()

    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())

    try:
        handle_relay_withdraw_create(
            network="crynux-on-base-sepolia",
            amount_wei="100",
            address="0x1111111111111111111111111111111111111111",
            relay_env="production",
        )
    except RuntimeError as exc:
        assert "INVALID_RELAY_NETWORK_PAIRING" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
