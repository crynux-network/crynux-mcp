from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    address: str
    kind: str
    status: str
    latest_record: dict[str, Any]
