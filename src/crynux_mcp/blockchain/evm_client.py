from __future__ import annotations

from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import HTTPProvider, Web3
from web3.exceptions import TransactionNotFound

from crynux_mcp.blockchain.schemas import (
    BalanceResult,
    BeneficialAddressResult,
    LatestBlockNumberResult,
    NodeCreditsResult,
    NodeStakingInfoResult,
    SetBeneficialAddressResult,
    TransferResult,
    Unit,
    normalize_unit,
    parse_amount_to_wei,
)
from crynux_mcp.config.loader import ChainConfig

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
BENEFICIAL_ADDRESS_ABI: list[dict[str, Any]] = [
    {
        "inputs": [{"internalType": "address", "name": "nodeAddress", "type": "address"}],
        "name": "getBenefitAddress",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "benefitAddress", "type": "address"}],
        "name": "setBenefitAddress",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

NODE_STAKING_ABI: list[dict[str, Any]] = [
    {
        "inputs": [{"internalType": "address", "name": "nodeAddress", "type": "address"}],
        "name": "getStakingInfo",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "nodeAddress", "type": "address"},
                    {"internalType": "uint256", "name": "stakedBalance", "type": "uint256"},
                    {"internalType": "uint256", "name": "stakedCredits", "type": "uint256"},
                    {"internalType": "uint8", "name": "status", "type": "uint8"},
                    {"internalType": "uint256", "name": "unstakeTimestamp", "type": "uint256"},
                ],
                "internalType": "struct NodeStaking.StakingInfo",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    }
]

CREDITS_ABI: list[dict[str, Any]] = [
    {
        "inputs": [{"internalType": "address", "name": "addr", "type": "address"}],
        "name": "getCredits",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]


class EvmClient:
    def __init__(self, chain: ChainConfig) -> None:
        self.chain = chain
        self.w3 = Web3(HTTPProvider(chain.rpc_url))

    def get_balance(self, address: str) -> BalanceResult:
        checksum = self._validate_address(address)
        balance_wei = self.w3.eth.get_balance(checksum)
        return BalanceResult(
            balance_wei=str(balance_wei),
            symbol=self.chain.native_currency.symbol,
        )

    def get_latest_block_number(self) -> LatestBlockNumberResult:
        return LatestBlockNumberResult(block_number=int(self.w3.eth.block_number))

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
            from_address=from_address,
            to=to_checksum,
            value_wei=str(value_wei),
            tx_hash=tx_hash,
        )

    def get_beneficial_address(self, node_address: str) -> BeneficialAddressResult:
        node_checksum = self._validate_address(node_address)
        _, contract = self._get_beneficial_contract()
        beneficial_address = contract.functions.getBenefitAddress(node_checksum).call()
        beneficial_checksum = self._validate_address(str(beneficial_address))
        is_set = beneficial_checksum.lower() != ZERO_ADDRESS.lower()
        return BeneficialAddressResult(
            address=node_checksum,
            beneficial_address=beneficial_checksum,
            is_set=is_set,
        )

    def set_beneficial_address(
        self,
        private_key: str,
        beneficial_address: str,
        gas_price_wei: int | None = None,
        gas_limit: int | None = None,
    ) -> SetBeneficialAddressResult:
        account = self._validate_private_key(private_key)
        beneficial_checksum = self._validate_address(beneficial_address)
        _, contract = self._get_beneficial_contract()

        provider_chain_id = int(self.w3.eth.chain_id)
        if provider_chain_id != self.chain.chain_id:
            raise ValueError(
                f"CHAIN_ID_MISMATCH: provider chain_id is {provider_chain_id}, expected {self.chain.chain_id}."
            )

        nonce = self.w3.eth.get_transaction_count(account.address, block_identifier="pending")
        effective_gas_price = gas_price_wei or int(self.w3.eth.gas_price)
        tx: dict[str, Any] = contract.functions.setBenefitAddress(beneficial_checksum).build_transaction(
            {
                "chainId": self.chain.chain_id,
                "from": account.address,
                "nonce": int(nonce),
                "gasPrice": int(effective_gas_price),
            }
        )
        tx["gas"] = int(gas_limit) if gas_limit else int(self.w3.eth.estimate_gas(tx))

        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        return SetBeneficialAddressResult(
            address=account.address,
            beneficial_address=beneficial_checksum,
            tx_hash=tx_hash,
        )

    def get_node_staking_info(self, node_address: str) -> NodeStakingInfoResult:
        node_checksum = self._validate_address(node_address)
        _, contract = self._get_contract(
            contract_key="node_staking",
            abi=NODE_STAKING_ABI,
        )
        staking_info = contract.functions.getStakingInfo(node_checksum).call()
        staking_node_address = self._validate_address(
            str(getattr(staking_info, "nodeAddress", None) or staking_info[0] or node_checksum)
        )
        staked_balance_wei = int(getattr(staking_info, "stakedBalance", None) or staking_info[1] or 0)
        staked_credits = int(getattr(staking_info, "stakedCredits", None) or staking_info[2] or 0)
        status = int(getattr(staking_info, "status", None) or staking_info[3] or 0)
        unstake_timestamp = int(getattr(staking_info, "unstakeTimestamp", None) or staking_info[4] or 0)
        return NodeStakingInfoResult(
            address=staking_node_address,
            staked_balance_wei=str(staked_balance_wei),
            staked_balance_formatted=str(Web3.from_wei(staked_balance_wei, "ether")),
            staked_credits=str(staked_credits),
            status=status,
            unstake_timestamp=str(unstake_timestamp),
        )

    def get_node_credits(self, node_address: str) -> NodeCreditsResult:
        account_address = self._validate_address(node_address)
        _, contract = self._get_contract(contract_key="credits", abi=CREDITS_ABI)
        credits = int(contract.functions.getCredits(account_address).call())
        return NodeCreditsResult(
            address=account_address,
            credits=str(credits),
            credits_formatted=str(Web3.from_wei(credits, "ether")),
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

    def _get_beneficial_contract(self) -> tuple[str, Any]:
        return self._get_contract(contract_key="beneficial_address", abi=BENEFICIAL_ADDRESS_ABI)

    def _get_contract(self, contract_key: str, abi: list[dict[str, Any]]) -> tuple[str, Any]:
        raw_address = str(self.chain.contracts.get(contract_key, "")).strip()
        if not raw_address:
            raise ValueError(f"MISSING_CONTRACT_ADDRESS: {contract_key} contract is not configured.")
        contract_address = self._validate_address(raw_address)
        contract = self.w3.eth.contract(address=contract_address, abi=abi)
        return contract_address, contract
