from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _select_latest_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None

    def sort_key(item: dict[str, Any]) -> tuple[int, int]:
        created_at = int(item.get("created_at", 0) or 0)
        identifier = int(item.get("id", 0) or 0)
        return (created_at, identifier)

    return max(records, key=sort_key)


@dataclass(frozen=True)
class RelayAuthSession:
    address: str
    token: str
    expires_at: int

    def to_dict(self) -> dict[str, Any]:
        return {"address": self.address, "token": self.token, "expires_at": self.expires_at}

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> RelayAuthSession:
        return RelayAuthSession(
            address=str(payload.get("address", "")).strip(),
            token=str(payload.get("token", "")).strip(),
            expires_at=int(payload.get("expires_at", 0)),
        )


@dataclass(frozen=True)
class RelayLatestStatusResult:
    kind: str
    status: str
    found: bool
    latest_record: dict[str, Any]

    @staticmethod
    def from_records(kind: str, records: list[dict[str, Any]]) -> "RelayLatestStatusResult":
        latest = _select_latest_record(records)
        status = str(latest.get("status", "")) if latest else ""
        return RelayLatestStatusResult(
            kind=kind,
            status=status,
            found=latest is not None,
            latest_record=latest or {},
        )


@dataclass(frozen=True)
class RelayAuthTokenResult:
    token: str
    expires_at: int
    refreshed: bool

    @staticmethod
    def from_session(session: "RelayAuthSession", *, refreshed: bool) -> "RelayAuthTokenResult":
        return RelayAuthTokenResult(token=session.token, expires_at=session.expires_at, refreshed=refreshed)

    def to_account_balance_result(self, balance_wei: str) -> "RelayAccountBalanceResult":
        return RelayAccountBalanceResult.create(balance_wei=balance_wei)


@dataclass(frozen=True)
class RelayAccountBalanceResult:
    balance_wei: str

    @staticmethod
    def create(balance_wei: str) -> "RelayAccountBalanceResult":
        return RelayAccountBalanceResult(balance_wei=balance_wei)


@dataclass(frozen=True)
class RelayWithdrawCreateResult:
    amount_wei: str
    benefit_address: str
    timestamp: int
    result: dict[str, Any]

    @staticmethod
    def create(amount_wei: str, benefit_address: str, timestamp: int, result: dict[str, Any]) -> "RelayWithdrawCreateResult":
        return RelayWithdrawCreateResult(
            amount_wei=amount_wei,
            benefit_address=benefit_address,
            timestamp=timestamp,
            result=result,
        )


@dataclass(frozen=True)
class RelayWithdrawListResult:
    page: int
    page_size: int
    total: int
    withdraw_records: list[dict[str, Any]]

    @staticmethod
    def create(page: int, page_size: int, total: int, withdraw_records: list[dict[str, Any]]) -> "RelayWithdrawListResult":
        return RelayWithdrawListResult(
            page=page,
            page_size=page_size,
            total=total,
            withdraw_records=withdraw_records,
        )


@dataclass(frozen=True)
class RelayDepositListResult:
    page: int
    page_size: int
    total: int
    deposit_records: list[dict[str, Any]]

    @staticmethod
    def create(page: int, page_size: int, total: int, deposit_records: list[dict[str, Any]]) -> "RelayDepositListResult":
        return RelayDepositListResult(
            page=page,
            page_size=page_size,
            total=total,
            deposit_records=deposit_records,
        )
