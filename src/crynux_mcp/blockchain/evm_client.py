from __future__ import annotations

from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import HTTPProvider, Web3
from web3.exceptions import TransactionNotFound

from crynux_mcp.blockchain.schemas import BalanceResult, TransferResult, Unit, normalize_unit, parse_amount_to_wei
from crynux_mcp.config.loader import ChainConfig


class EvmClient:
    def __init__(self, chain: ChainConfig) -> None:
        self.chain = chain
        self.w3 = Web3(HTTPProvider(chain.rpc_url))

    def get_balance(self, address: str, unit: str | None = None) -> BalanceResult:
        checksum = self._validate_address(address)
        normalized_unit = normalize_unit(unit)
        balance_wei = self.w3.eth.get_balance(checksum)
        if normalized_unit == "wei":
            balance_formatted = str(balance_wei)
        else:
            balance_formatted = str(Web3.from_wei(balance_wei, "ether"))
        return BalanceResult(
            network=self.chain.network_key,
            address=checksum,
            balance_wei=str(balance_wei),
            balance_formatted=balance_formatted,
            symbol=self.chain.native_currency.symbol,
            chain_id=self.chain.chain_id,
        )

    def transfer_native(
        self,
        private_key: str,
        to: str,
        amount: str,
        unit: str | None = None,
        gas_price_wei: int | None = None,
        gas_limit: int | None = None,
    ) -> TransferResult:
        normalized_unit: Unit = normalize_unit(unit)
        account = self._validate_private_key(private_key)
        to_checksum = self._validate_address(to)
        value_wei = parse_amount_to_wei(amount=amount, unit=normalized_unit)

        provider_chain_id = int(self.w3.eth.chain_id)
        if provider_chain_id != self.chain.chain_id:
            raise ValueError(
                f"CHAIN_ID_MISMATCH: provider chain_id is {provider_chain_id}, expected {self.chain.chain_id}."
            )

        from_address = account.address
        nonce = self.w3.eth.get_transaction_count(from_address, block_identifier="pending")
        effective_gas_price = gas_price_wei or int(self.w3.eth.gas_price)

        tx: dict[str, Any] = {
            "chainId": self.chain.chain_id,
            "from": from_address,
            "to": to_checksum,
            "value": int(value_wei),
            "nonce": int(nonce),
            "gasPrice": int(effective_gas_price),
        }

        tx["gas"] = int(gas_limit) if gas_limit else int(self.w3.eth.estimate_gas(tx))
        signed = account.sign_transaction(tx)
        tx_hash_bytes = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash = tx_hash_bytes.hex()

        return TransferResult(
            network=self.chain.network_key,
            from_address=from_address,
            to=to_checksum,
            value_wei=str(value_wei),
            tx_hash=tx_hash,
            chain_id=self.chain.chain_id,
        )

    def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any]:
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound as exc:
            raise ValueError("TX_NOT_FOUND: transaction receipt is not available yet.") from exc
        return dict(receipt)

    def _validate_address(self, address: str) -> str:
        if not isinstance(address, str) or not address.strip():
            raise ValueError("INVALID_ADDRESS: address is required.")
        if not Web3.is_address(address):
            raise ValueError("INVALID_ADDRESS: address is not a valid EVM address.")
        return Web3.to_checksum_address(address)

    def _validate_private_key(self, private_key: str) -> LocalAccount:
        raw = (private_key or "").strip()
        if not raw:
            raise ValueError("INVALID_PRIVATE_KEY: private key is required.")
        try:
            return Account.from_key(raw)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("INVALID_PRIVATE_KEY: private key is invalid.") from exc
