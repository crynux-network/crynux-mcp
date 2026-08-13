from dataclasses import dataclass

from crynux_mcp.server import (
    handle_delegated_stake,
    handle_delegated_unstake,
    handle_force_unstake_node,
    handle_get_balance,
    handle_get_beneficial_address,
    handle_get_delegated_staking_infos,
    handle_get_latest_block_number,
    handle_get_node_staking_info,
    handle_send_raw_transaction,
    handle_set_beneficial_address,
    handle_sign_transaction,
    handle_transfer_native,
    handle_try_unstake_node,
)


def test_handle_get_balance_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        balance_wei: str = "100"
        symbol: str = "CNX"

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def get_balance(self, address: str):
            _ = address
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())

    payload = handle_get_balance(
        network="crynux-on-base",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["symbol"] == "CNX"
    assert "network" not in payload
    assert "address" not in payload
    assert "chain_id" not in payload


def test_handle_get_latest_block_number_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        block_number: int = 123456

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def get_latest_block_number(self):
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())

    payload = handle_get_latest_block_number(network="crynux-on-base")
    assert payload["block_number"] == 123456
    assert "network" not in payload
    assert "chain_id" not in payload


def test_handle_transfer_sanitizes_private_key_error(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def transfer_native(self, **_kwargs):
            raise ValueError("private key must be 32 bytes")

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: "0xabc")

    try:
        handle_transfer_native(
            network="crynux-on-base",
            to="0x1111111111111111111111111111111111111111",
            amount="1",
        )
    except RuntimeError as exc:
        assert str(exc) == "INVALID_PRIVATE_KEY: private key is invalid."
    else:
        raise AssertionError("Expected RuntimeError")


def test_handle_transfer_requires_private_key_source(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def transfer_native(self, **_kwargs):
            return object()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())
    monkeypatch.setattr(
        "crynux_mcp.server.get_private_key",
        lambda name=None: (_ for _ in ()).throw(ValueError("MISSING_PRIVATE_KEY: no signer key found.")),
    )

    try:
        handle_transfer_native(
            network="crynux-on-base",
            to="0x1111111111111111111111111111111111111111",
            amount="1",
        )
    except RuntimeError as exc:
        assert str(exc) == "MISSING_PRIVATE_KEY: no signer key found."
    else:
        raise AssertionError("Expected RuntimeError")


def test_handle_sign_transaction_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        from_address: str = "0x1111111111111111111111111111111111111111"
        to: str = "0x2222222222222222222222222222222222222222"
        value_wei: str = "0"
        data: str = "0xabcdef"
        nonce: int = 7
        gas: int = 21000
        gas_price_wei: str = "100"
        chain_id: int = 18896214
        raw_transaction: str = "0xf86c"
        tx_hash: str = "0xabc"

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def sign_transaction(self, **_kwargs):
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: "0xabc")

    payload = handle_sign_transaction(
        network="crynux-on-base",
        to="0x2222222222222222222222222222222222222222",
        data="0xabcdef",
    )
    assert payload["raw_transaction"] == "0xf86c"
    assert payload["tx_hash"] == "0xabc"
    assert payload["data"] == "0xabcdef"
    assert "private_key" not in payload
    assert "network" not in payload


def test_handle_send_raw_transaction_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        tx_hash: str = "0xdef"

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def send_raw_transaction(self, raw_transaction: str):
            assert raw_transaction == "0xf86c"
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())

    payload = handle_send_raw_transaction(network="crynux-on-base", raw_transaction="0xf86c")
    assert payload["tx_hash"] == "0xdef"
    assert "network" not in payload


def test_handle_get_beneficial_address_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        address: str = "0x1111111111111111111111111111111111111111"
        beneficial_address: str = "0x2222222222222222222222222222222222222222"
        is_set: bool = True

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def get_beneficial_address(self, node_address: str):
            _ = node_address
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())

    payload = handle_get_beneficial_address(
        network="crynux-on-base",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["address"] == "0x1111111111111111111111111111111111111111"
    assert payload["beneficial_address"] == "0x2222222222222222222222222222222222222222"
    assert payload["is_set"] is True
    assert "network" not in payload
    assert "contract_address" not in payload
    assert "chain_id" not in payload


def test_handle_set_beneficial_address_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        address: str = "0x1111111111111111111111111111111111111111"
        beneficial_address: str = "0x2222222222222222222222222222222222222222"
        tx_hash: str = "0xabc"

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def set_beneficial_address(self, **_kwargs):
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: "0xabc")

    payload = handle_set_beneficial_address(
        network="crynux-on-base",
        beneficial_address="0x2222222222222222222222222222222222222222",
    )
    assert payload["address"] == "0x1111111111111111111111111111111111111111"
    assert payload["tx_hash"] == "0xabc"
    assert payload["beneficial_address"] == "0x2222222222222222222222222222222222222222"
    assert "network" not in payload
    assert "contract_address" not in payload
    assert "chain_id" not in payload


def test_handle_get_node_staking_info_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        address: str = "0x1111111111111111111111111111111111111111"
        staked_balance_wei: str = "1000000000000000000"
        staked_balance_formatted: str = "1"
        status: int = 2
        unstake_timestamp: str = "1000"
        force_unstake_delay_seconds: str = "1800"
        force_unstake_available_at: str = "2801"
        force_unstake_available_in_seconds: str = "120"
        can_force_unstake: bool = False

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def get_node_staking_info(self, node_address: str):
            _ = node_address
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())

    payload = handle_get_node_staking_info(
        network="crynux-on-base",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["address"] == "0x1111111111111111111111111111111111111111"
    assert payload["staked_balance_wei"] == "1000000000000000000"
    assert payload["status"] == 2
    assert payload["force_unstake_delay_seconds"] == "1800"
    assert payload["force_unstake_available_at"] == "2801"
    assert payload["force_unstake_available_in_seconds"] == "120"
    assert payload["can_force_unstake"] is False
    assert "staked_credits" not in payload
    assert "network" not in payload
    assert "contract_address" not in payload
    assert "chain_id" not in payload


def test_handle_try_unstake_node_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        address: str = "0x1111111111111111111111111111111111111111"
        tx_hash: str = "0xabc"

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def try_unstake_node(self, **_kwargs):
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: "0xabc")

    payload = handle_try_unstake_node(network="crynux-on-base")
    assert payload["address"] == "0x1111111111111111111111111111111111111111"
    assert payload["tx_hash"] == "0xabc"
    assert "network" not in payload


def test_handle_force_unstake_node_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        address: str = "0x1111111111111111111111111111111111111111"
        unstaked_amount_wei: str = "1000000000000000000"
        tx_hash: str = "0xdef"

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def force_unstake_node(self, **_kwargs):
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: "0xabc")

    payload = handle_force_unstake_node(network="crynux-on-base")
    assert payload["address"] == "0x1111111111111111111111111111111111111111"
    assert payload["unstaked_amount_wei"] == "1000000000000000000"
    assert payload["tx_hash"] == "0xdef"
    assert "network" not in payload


def test_handle_get_delegated_staking_infos_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeEntry:
        node_address: str
        stake_amount_wei: str
        stake_amount_formatted: str

    @dataclass(frozen=True)
    class FakeResult:
        address: str
        total_stake_wei: str
        total_stake_formatted: str
        stakes: list[FakeEntry]

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def get_delegated_staking_infos(self, delegator_address: str):
            assert delegator_address == "0x1111111111111111111111111111111111111111"
            return FakeResult(
                address="0x1111111111111111111111111111111111111111",
                total_stake_wei="1000000000000000000",
                total_stake_formatted="1",
                stakes=[
                    FakeEntry(
                        node_address="0x2222222222222222222222222222222222222222",
                        stake_amount_wei="1000000000000000000",
                        stake_amount_formatted="1",
                    )
                ],
            )

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())

    payload = handle_get_delegated_staking_infos(
        network="crynux-on-base",
        address="0x1111111111111111111111111111111111111111",
    )
    assert payload["address"] == "0x1111111111111111111111111111111111111111"
    assert payload["total_stake_wei"] == "1000000000000000000"
    assert len(payload["stakes"]) == 1
    assert payload["stakes"][0]["node_address"] == "0x2222222222222222222222222222222222222222"
    assert "network" not in payload


def test_handle_delegated_stake_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        address: str = "0x1111111111111111111111111111111111111111"
        node_address: str = "0x2222222222222222222222222222222222222222"
        previous_amount_wei: str = "0"
        stake_amount_wei: str = "2000000000000000000"
        value_sent_wei: str = "2000000000000000000"
        tx_hash: str = "0xabc"

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def delegated_stake(self, **_kwargs):
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: "0xabc")

    payload = handle_delegated_stake(
        network="crynux-on-base",
        node_address="0x2222222222222222222222222222222222222222",
        amount="2",
    )
    assert payload["node_address"] == "0x2222222222222222222222222222222222222222"
    assert payload["stake_amount_wei"] == "2000000000000000000"
    assert payload["value_sent_wei"] == "2000000000000000000"
    assert payload["tx_hash"] == "0xabc"
    assert "network" not in payload


def test_handle_delegated_unstake_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    @dataclass(frozen=True)
    class FakeResult:
        address: str = "0x1111111111111111111111111111111111111111"
        node_address: str = "0x2222222222222222222222222222222222222222"
        unstaked_amount_wei: str = "1000000000000000000"
        tx_hash: str = "0xdef"

    class FakeClient:
        def __init__(self, _chain) -> None:
            pass

        def delegated_unstake(self, **_kwargs):
            return FakeResult()

    class FakeRegistry:
        def resolve(self, _network):
            return object()

    monkeypatch.setattr("crynux_mcp.server.EvmClient", FakeClient)
    monkeypatch.setattr("crynux_mcp.server.registry", FakeRegistry())
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: "0xabc")

    payload = handle_delegated_unstake(
        network="crynux-on-base",
        node_address="0x2222222222222222222222222222222222222222",
    )
    assert payload["node_address"] == "0x2222222222222222222222222222222222222222"
    assert payload["unstaked_amount_wei"] == "1000000000000000000"
    assert payload["tx_hash"] == "0xdef"
    assert "network" not in payload
