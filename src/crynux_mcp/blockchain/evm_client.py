from __future__ import annotations

from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import HTTPProvider, Web3
from web3.exceptions import TransactionNotFound

from crynux_mcp.blockchain.schemas import (
    BalanceResult,
    BeneficialAddressResult,
    DelegatedStakeResult,
    DelegatedStakingEntry,
    DelegatedStakingInfosResult,
    DelegatedUnstakeResult,
    LatestBlockNumberResult,
    NodeForceUnstakeResult,
    NodeStakeResult,
    NodeStakingInfoResult,
    NodeTryUnstakeResult,
    SendRawTransactionResult,
    SetBeneficialAddressResult,
    SignTransactionResult,
    TransferResult,
    Unit,
    normalize_unit,
    parse_amount_to_wei,
    parse_non_negative_amount_to_wei,
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
    },
    {
        "inputs": [],
        "name": "getForceUnstakeDelay",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getMinStakeAmount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "stakedAmount", "type": "uint256"}],
        "name": "stake",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "tryUnstake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "forceUnstake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

DELEGATED_STAKING_ABI: list[dict[str, Any]] = [
    {
        "inputs": [{"internalType": "address", "name": "delegatorAddress", "type": "address"}],
        "name": "getDelegatorStakingInfos",
        "outputs": [
            {"internalType": "address[]", "name": "", "type": "address[]"},
            {"internalType": "uint256[]", "name": "", "type": "uint256[]"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "delegatorAddress", "type": "address"}],
        "name": "getDelegatorTotalStakeAmount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "delegatorAddress", "type": "address"},
            {"internalType": "address", "name": "nodeAddress", "type": "address"},
        ],
        "name": "getDelegationStakingAmount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getMinStakeAmount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "nodeAddress", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "stake",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "nodeAddress", "type": "address"}],
        "name": "unstake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
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

    def sign_transaction(
        self,
        private_key: str,
        to: str | None = None,
        value: str | None = "0",
        unit: str | None = "wei",
        data: str | None = "0x",
        nonce: int | None = None,
        gas_price_wei: int | None = None,
        gas_limit: int | None = None,
    ) -> SignTransactionResult:
        normalized_unit: Unit = normalize_unit(unit)
        account = self._validate_private_key(private_key)
        value_wei = parse_non_negative_amount_to_wei(amount=value or "0", unit=normalized_unit)
        data_hex = self._normalize_tx_data(data)
        to_checksum = self._validate_address(to) if (to or "").strip() else ""
        if not to_checksum and data_hex in {"0x", "0X"}:
            raise ValueError("INVALID_TRANSACTION: provide 'to' or non-empty 'data'.")

        self._assert_provider_chain_id()
        from_address = account.address
        effective_nonce = (
            int(nonce)
            if nonce is not None
            else int(self.w3.eth.get_transaction_count(from_address, block_identifier="pending"))
        )
        if effective_nonce < 0:
            raise ValueError("INVALID_NONCE: nonce must be greater than or equal to 0.")
        effective_gas_price = gas_price_wei or int(self.w3.eth.gas_price)
        if int(effective_gas_price) <= 0:
            raise ValueError("INVALID_GAS_PRICE: gas_price_wei must be greater than 0.")

        tx: dict[str, Any] = {
            "chainId": self.chain.chain_id,
            "from": from_address,
            "value": int(value_wei),
            "nonce": int(effective_nonce),
            "gasPrice": int(effective_gas_price),
            "data": data_hex,
        }
        if to_checksum:
            tx["to"] = to_checksum

        if gas_limit is not None:
            if int(gas_limit) <= 0:
                raise ValueError("INVALID_GAS_LIMIT: gas_limit must be greater than 0.")
            tx["gas"] = int(gas_limit)
        else:
            tx["gas"] = int(self.w3.eth.estimate_gas(tx))

        signed = account.sign_transaction(tx)
        raw_transaction = self._normalize_hex_bytes(signed.raw_transaction)
        tx_hash = self._normalize_hex_bytes(signed.hash)
        return SignTransactionResult(
            from_address=from_address,
            to=to_checksum,
            value_wei=str(value_wei),
            data=data_hex,
            nonce=int(effective_nonce),
            gas=int(tx["gas"]),
            gas_price_wei=str(int(effective_gas_price)),
            chain_id=int(self.chain.chain_id),
            raw_transaction=raw_transaction,
            tx_hash=tx_hash,
        )

    def send_raw_transaction(self, raw_transaction: str) -> SendRawTransactionResult:
        raw_hex = self._normalize_tx_data(raw_transaction)
        if raw_hex in {"0x", "0X"}:
            raise ValueError("INVALID_RAW_TRANSACTION: raw_transaction is required.")
        self._assert_provider_chain_id()
        tx_hash_bytes = self.w3.eth.send_raw_transaction(raw_hex)
        return SendRawTransactionResult(tx_hash=self._normalize_hex_bytes(tx_hash_bytes))

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
        status = int(getattr(staking_info, "status", None) or staking_info[2] or 0)
        unstake_timestamp = int(getattr(staking_info, "unstakeTimestamp", None) or staking_info[3] or 0)
        force_unstake_delay = int(contract.functions.getForceUnstakeDelay().call())
        latest_block = self.w3.eth.get_block("latest")
        now_seconds = int(latest_block["timestamp"])

        # Contract requires: unstakeTimestamp + forceUnstakeDelay < block.timestamp
        force_available_at = 0
        force_available_in_seconds = 0
        can_force_unstake = False
        if status == 2 and unstake_timestamp > 0:
            force_available_at = unstake_timestamp + force_unstake_delay + 1
            if now_seconds >= force_available_at:
                can_force_unstake = True
                force_available_in_seconds = 0
            else:
                force_available_in_seconds = force_available_at - now_seconds

        return NodeStakingInfoResult(
            address=staking_node_address if staking_node_address != ZERO_ADDRESS else node_checksum,
            staked_balance_wei=str(staked_balance_wei),
            staked_balance_formatted=str(Web3.from_wei(staked_balance_wei, "ether")),
            status=status,
            unstake_timestamp=str(unstake_timestamp),
            force_unstake_delay_seconds=str(force_unstake_delay),
            force_unstake_available_at=str(force_available_at),
            force_unstake_available_in_seconds=str(force_available_in_seconds),
            can_force_unstake=can_force_unstake,
        )

    def stake_node(
        self,
        private_key: str,
        amount: str,
        unit: str | None = None,
        gas_price_wei: int | None = None,
        gas_limit: int | None = None,
    ) -> NodeStakeResult:
        normalized_unit: Unit = normalize_unit(unit)
        account = self._validate_private_key(private_key)
        target_amount_wei = parse_amount_to_wei(amount=amount, unit=normalized_unit)
        _, contract = self._get_contract(contract_key="node_staking", abi=NODE_STAKING_ABI)

        min_stake_wei = int(contract.functions.getMinStakeAmount().call())
        if target_amount_wei < min_stake_wei:
            raise ValueError(
                "INVALID_AMOUNT: stake amount must be greater than or equal to "
                f"minimum stake amount ({min_stake_wei} wei)."
            )

        staking_info = contract.functions.getStakingInfo(account.address).call()
        previous_amount_wei = int(getattr(staking_info, "stakedBalance", None) or staking_info[1] or 0)
        status = int(getattr(staking_info, "status", None) or staking_info[2] or 0)
        if status == 2:
            raise ValueError(
                "INVALID_STAKING_STATUS: stake requires status Unstaked (0) or Staked (1), "
                f"current status is {status}."
            )

        if target_amount_wei > previous_amount_wei:
            value_sent_wei = target_amount_wei - previous_amount_wei
        else:
            value_sent_wei = 0

        self._assert_provider_chain_id()
        nonce = self.w3.eth.get_transaction_count(account.address, block_identifier="pending")
        effective_gas_price = gas_price_wei or int(self.w3.eth.gas_price)
        tx: dict[str, Any] = contract.functions.stake(int(target_amount_wei)).build_transaction(
            {
                "chainId": self.chain.chain_id,
                "from": account.address,
                "nonce": int(nonce),
                "gasPrice": int(effective_gas_price),
                "value": int(value_sent_wei),
            }
        )
        tx["gas"] = int(gas_limit) if gas_limit else int(self.w3.eth.estimate_gas(tx))
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        return NodeStakeResult(
            address=account.address,
            previous_amount_wei=str(previous_amount_wei),
            stake_amount_wei=str(target_amount_wei),
            value_sent_wei=str(value_sent_wei),
            tx_hash=tx_hash,
        )

    def try_unstake_node(
        self,
        private_key: str,
        gas_price_wei: int | None = None,
        gas_limit: int | None = None,
    ) -> NodeTryUnstakeResult:
        account = self._validate_private_key(private_key)
        _, contract = self._get_contract(contract_key="node_staking", abi=NODE_STAKING_ABI)
        staking_info = contract.functions.getStakingInfo(account.address).call()
        status = int(getattr(staking_info, "status", None) or staking_info[2] or 0)
        if status != 1:
            raise ValueError(
                "INVALID_STAKING_STATUS: tryUnstake requires status Staked (1), "
                f"current status is {status}."
            )

        self._assert_provider_chain_id()
        nonce = self.w3.eth.get_transaction_count(account.address, block_identifier="pending")
        effective_gas_price = gas_price_wei or int(self.w3.eth.gas_price)
        tx: dict[str, Any] = contract.functions.tryUnstake().build_transaction(
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
        return NodeTryUnstakeResult(address=account.address, tx_hash=tx_hash)

    def force_unstake_node(
        self,
        private_key: str,
        gas_price_wei: int | None = None,
        gas_limit: int | None = None,
    ) -> NodeForceUnstakeResult:
        account = self._validate_private_key(private_key)
        _, contract = self._get_contract(contract_key="node_staking", abi=NODE_STAKING_ABI)
        staking_info = contract.functions.getStakingInfo(account.address).call()
        staked_balance_wei = int(getattr(staking_info, "stakedBalance", None) or staking_info[1] or 0)
        status = int(getattr(staking_info, "status", None) or staking_info[2] or 0)
        unstake_timestamp = int(getattr(staking_info, "unstakeTimestamp", None) or staking_info[3] or 0)
        if status != 2:
            raise ValueError(
                "INVALID_STAKING_STATUS: forceUnstake requires status PendingUnstaked (2), "
                f"current status is {status}."
            )
        force_unstake_delay = int(contract.functions.getForceUnstakeDelay().call())
        latest_block = self.w3.eth.get_block("latest")
        now_seconds = int(latest_block["timestamp"])
        if now_seconds <= unstake_timestamp + force_unstake_delay:
            available_at = unstake_timestamp + force_unstake_delay + 1
            remaining = max(0, available_at - now_seconds)
            raise ValueError(
                "FORCE_UNSTAKE_NOT_READY: force unstake is not available yet. "
                f"Available in {remaining} seconds (at unix timestamp {available_at})."
            )

        self._assert_provider_chain_id()
        nonce = self.w3.eth.get_transaction_count(account.address, block_identifier="pending")
        effective_gas_price = gas_price_wei or int(self.w3.eth.gas_price)
        tx: dict[str, Any] = contract.functions.forceUnstake().build_transaction(
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
        return NodeForceUnstakeResult(
            address=account.address,
            unstaked_amount_wei=str(staked_balance_wei),
            tx_hash=tx_hash,
        )

    def get_delegated_staking_infos(self, delegator_address: str) -> DelegatedStakingInfosResult:
        delegator_checksum = self._validate_address(delegator_address)
        _, contract = self._get_contract(contract_key="delegated_staking", abi=DELEGATED_STAKING_ABI)
        nodes, amounts = contract.functions.getDelegatorStakingInfos(delegator_checksum).call()
        total_stake_wei = int(contract.functions.getDelegatorTotalStakeAmount(delegator_checksum).call())
        stakes: list[DelegatedStakingEntry] = []
        for node_raw, amount_raw in zip(nodes, amounts, strict=True):
            amount_wei = int(amount_raw)
            stakes.append(
                DelegatedStakingEntry(
                    node_address=self._validate_address(str(node_raw)),
                    stake_amount_wei=str(amount_wei),
                    stake_amount_formatted=str(Web3.from_wei(amount_wei, "ether")),
                )
            )
        return DelegatedStakingInfosResult(
            address=delegator_checksum,
            total_stake_wei=str(total_stake_wei),
            total_stake_formatted=str(Web3.from_wei(total_stake_wei, "ether")),
            stakes=stakes,
        )

    def delegated_stake(
        self,
        private_key: str,
        node_address: str,
        amount: str,
        unit: str | None = None,
        gas_price_wei: int | None = None,
        gas_limit: int | None = None,
    ) -> DelegatedStakeResult:
        normalized_unit: Unit = normalize_unit(unit)
        account = self._validate_private_key(private_key)
        node_checksum = self._validate_address(node_address)
        target_amount_wei = parse_amount_to_wei(amount=amount, unit=normalized_unit)
        _, contract = self._get_contract(contract_key="delegated_staking", abi=DELEGATED_STAKING_ABI)

        min_stake_wei = int(contract.functions.getMinStakeAmount().call())
        if target_amount_wei < min_stake_wei:
            raise ValueError(
                "INVALID_AMOUNT: stake amount must be greater than or equal to "
                f"minimum stake amount ({min_stake_wei} wei)."
            )

        previous_amount_wei = int(
            contract.functions.getDelegationStakingAmount(account.address, node_checksum).call()
        )
        if target_amount_wei > previous_amount_wei:
            value_sent_wei = target_amount_wei - previous_amount_wei
        else:
            value_sent_wei = 0

        self._assert_provider_chain_id()
        nonce = self.w3.eth.get_transaction_count(account.address, block_identifier="pending")
        effective_gas_price = gas_price_wei or int(self.w3.eth.gas_price)
        tx: dict[str, Any] = contract.functions.stake(node_checksum, int(target_amount_wei)).build_transaction(
            {
                "chainId": self.chain.chain_id,
                "from": account.address,
                "nonce": int(nonce),
                "gasPrice": int(effective_gas_price),
                "value": int(value_sent_wei),
            }
        )
        tx["gas"] = int(gas_limit) if gas_limit else int(self.w3.eth.estimate_gas(tx))
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        return DelegatedStakeResult(
            address=account.address,
            node_address=node_checksum,
            previous_amount_wei=str(previous_amount_wei),
            stake_amount_wei=str(target_amount_wei),
            value_sent_wei=str(value_sent_wei),
            tx_hash=tx_hash,
        )

    def delegated_unstake(
        self,
        private_key: str,
        node_address: str,
        gas_price_wei: int | None = None,
        gas_limit: int | None = None,
    ) -> DelegatedUnstakeResult:
        account = self._validate_private_key(private_key)
        node_checksum = self._validate_address(node_address)
        _, contract = self._get_contract(contract_key="delegated_staking", abi=DELEGATED_STAKING_ABI)
        previous_amount_wei = int(
            contract.functions.getDelegationStakingAmount(account.address, node_checksum).call()
        )
        if previous_amount_wei <= 0:
            raise ValueError("NO_DELEGATED_STAKE: no delegated stake exists for this node address.")

        self._assert_provider_chain_id()
        nonce = self.w3.eth.get_transaction_count(account.address, block_identifier="pending")
        effective_gas_price = gas_price_wei or int(self.w3.eth.gas_price)
        tx: dict[str, Any] = contract.functions.unstake(node_checksum).build_transaction(
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
        return DelegatedUnstakeResult(
            address=account.address,
            node_address=node_checksum,
            unstaked_amount_wei=str(previous_amount_wei),
            tx_hash=tx_hash,
        )

    def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any]:
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound as exc:
            raise ValueError("TX_NOT_FOUND: transaction receipt is not available yet.") from exc
        return dict(receipt)

    def _assert_provider_chain_id(self) -> None:
        provider_chain_id = int(self.w3.eth.chain_id)
        if provider_chain_id != self.chain.chain_id:
            raise ValueError(
                f"CHAIN_ID_MISMATCH: provider chain_id is {provider_chain_id}, expected {self.chain.chain_id}."
            )

    def _normalize_tx_data(self, data: str | None) -> str:
        raw = (data or "").strip()
        if not raw:
            return "0x"
        if raw.lower().startswith("0x"):
            body = raw[2:]
        else:
            body = raw
        if len(body) % 2 != 0:
            raise ValueError("INVALID_TRANSACTION_DATA: data must be even-length hex.")
        try:
            bytes.fromhex(body)
        except ValueError as exc:
            raise ValueError("INVALID_TRANSACTION_DATA: data must be valid hexadecimal.") from exc
        return f"0x{body}"

    def _normalize_hex_bytes(self, value: Any) -> str:
        if hasattr(value, "hex"):
            raw = value.hex()
        else:
            raw = str(value)
        raw = raw.strip()
        if raw.lower().startswith("0x"):
            return f"0x{raw[2:]}"
        return f"0x{raw}"

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
