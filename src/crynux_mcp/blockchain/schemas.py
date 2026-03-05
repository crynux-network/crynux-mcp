from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


Unit = Literal["wei", "ether"]


@dataclass(frozen=True)
class BalanceResult:
    network: str
    address: str
    balance_wei: str
    balance_formatted: str
    symbol: str
    chain_id: int


@dataclass(frozen=True)
class TransferResult:
    network: str
    from_address: str
    to: str
    value_wei: str
    tx_hash: str
    chain_id: int


@dataclass(frozen=True)
class BeneficialAddressResult:
    network: str
    node_address: str
    beneficial_address: str
    is_set: bool
    contract_address: str
    chain_id: int


@dataclass(frozen=True)
class SetBeneficialAddressResult:
    network: str
    node_address: str
    beneficial_address: str
    tx_hash: str
    contract_address: str
    chain_id: int


@dataclass(frozen=True)
class NodeStakingInfoResult:
    network: str
    node_address: str
    staked_balance_wei: str
    staked_balance_formatted: str
    staked_credits: str
    status: int
    unstake_timestamp: str
    contract_address: str
    chain_id: int


@dataclass(frozen=True)
class NodeCreditsResult:
    network: str
    node_address: str
    credits: str
    credits_formatted: str
    contract_address: str
    chain_id: int


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
