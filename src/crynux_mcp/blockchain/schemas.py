from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


Unit = Literal["wei", "ether"]


@dataclass(frozen=True)
class BalanceResult:
    balance_wei: str
    symbol: str


@dataclass(frozen=True)
class LatestBlockNumberResult:
    block_number: int


@dataclass(frozen=True)
class TransferResult:
    from_address: str
    to: str
    value_wei: str
    tx_hash: str


@dataclass(frozen=True)
class SignTransactionResult:
    from_address: str
    to: str
    value_wei: str
    data: str
    nonce: int
    gas: int
    gas_price_wei: str
    chain_id: int
    raw_transaction: str
    tx_hash: str


@dataclass(frozen=True)
class SendRawTransactionResult:
    tx_hash: str


@dataclass(frozen=True)
class BeneficialAddressResult:
    address: str
    beneficial_address: str
    is_set: bool


@dataclass(frozen=True)
class SetBeneficialAddressResult:
    address: str
    beneficial_address: str
    tx_hash: str


@dataclass(frozen=True)
class NodeStakeResult:
    address: str
    previous_amount_wei: str
    stake_amount_wei: str
    value_sent_wei: str
    tx_hash: str


@dataclass(frozen=True)
class NodeStakingInfoResult:
    address: str
    staked_balance_wei: str
    staked_balance_formatted: str
    status: int
    unstake_timestamp: str
    force_unstake_delay_seconds: str
    force_unstake_available_at: str
    force_unstake_available_in_seconds: str
    can_force_unstake: bool


@dataclass(frozen=True)
class NodeTryUnstakeResult:
    address: str
    tx_hash: str


@dataclass(frozen=True)
class NodeForceUnstakeResult:
    address: str
    unstaked_amount_wei: str
    tx_hash: str


@dataclass(frozen=True)
class DelegatedStakingEntry:
    node_address: str
    stake_amount_wei: str
    stake_amount_formatted: str


@dataclass(frozen=True)
class DelegatedStakingInfosResult:
    address: str
    total_stake_wei: str
    total_stake_formatted: str
    stakes: list[DelegatedStakingEntry]


@dataclass(frozen=True)
class DelegatedStakeResult:
    address: str
    node_address: str
    previous_amount_wei: str
    stake_amount_wei: str
    value_sent_wei: str
    tx_hash: str


@dataclass(frozen=True)
class DelegatedUnstakeResult:
    address: str
    node_address: str
    unstaked_amount_wei: str
    tx_hash: str


def normalize_unit(unit: str | None) -> Unit:
    if unit is None:
        return "ether"
    normalized = unit.strip().lower()
    if normalized not in {"wei", "ether"}:
        raise ValueError("INVALID_UNIT: unit must be 'wei' or 'ether'.")
    return normalized  # type: ignore[return-value]


def parse_amount_to_wei(amount: str, unit: Unit) -> int:
    try:
        raw = Decimal(amount)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("INVALID_AMOUNT: amount must be a valid number string.") from exc

    if raw <= 0:
        raise ValueError("INVALID_AMOUNT: amount must be greater than 0.")

    if unit == "wei":
        if raw != raw.to_integral_value():
            raise ValueError("INVALID_AMOUNT: wei amount must be an integer.")
        return int(raw)

    scaled = raw * (Decimal(10) ** 18)
    if scaled != scaled.to_integral_value():
        raise ValueError("INVALID_AMOUNT: too many decimal places for ether unit.")
    return int(scaled)


def parse_non_negative_amount_to_wei(amount: str, unit: Unit) -> int:
    try:
        raw = Decimal(amount)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("INVALID_AMOUNT: amount must be a valid number string.") from exc

    if raw < 0:
        raise ValueError("INVALID_AMOUNT: amount must be greater than or equal to 0.")

    if unit == "wei":
        if raw != raw.to_integral_value():
            raise ValueError("INVALID_AMOUNT: wei amount must be an integer.")
        return int(raw)

    scaled = raw * (Decimal(10) ** 18)
    if scaled != scaled.to_integral_value():
        raise ValueError("INVALID_AMOUNT: too many decimal places for ether unit.")
    return int(scaled)
