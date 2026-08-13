from eth_account import Account

from crynux_mcp.blockchain.evm_client import EvmClient
from crynux_mcp.config.loader import ChainConfig, NativeCurrency


def _fake_chain() -> ChainConfig:
    return ChainConfig(
        network_key="crynux-on-base",
        network_kind="mainnet",
        chain_id=18896214,
        chain_name="Crynux on Base",
        rpc_url="https://json-rpc.base.crynux.io",
        native_currency=NativeCurrency(name="Crynux", symbol="CNX", decimals=18),
        contracts={},
    )


def test_sign_transaction_returns_raw_tx_without_broadcast(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    account = Account.create()
    captured: dict[str, object] = {}

    class FakeEth:
        chain_id = 18896214
        gas_price = 100

        def get_transaction_count(self, address, block_identifier="pending"):
            _ = address
            _ = block_identifier
            return 3

        def estimate_gas(self, tx):
            captured["estimate_tx"] = tx
            return 21000

        def send_raw_transaction(self, raw_transaction):
            raise AssertionError(f"broadcast should not happen: {raw_transaction}")

    class FakeW3:
        eth = FakeEth()

    client = EvmClient(_fake_chain())
    monkeypatch.setattr(client, "w3", FakeW3())
    result = client.sign_transaction(
        private_key=account.key.hex(),
        to="0x2222222222222222222222222222222222222222",
        value="0",
        data="0xabcdef",
    )

    assert result.from_address == account.address
    assert result.to == "0x2222222222222222222222222222222222222222"
    assert result.value_wei == "0"
    assert result.data == "0xabcdef"
    assert result.nonce == 3
    assert result.gas == 21000
    assert result.gas_price_wei == "100"
    assert result.chain_id == 18896214
    assert result.raw_transaction.startswith("0x")
    assert result.tx_hash.startswith("0x")
    assert "private_key" not in result.__dict__
