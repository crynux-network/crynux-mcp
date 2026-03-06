from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class KeyListResult:
    keys: list[dict[str, Any]]
    count: int

    @staticmethod
    def from_keys(keys: list[dict[str, Any]]) -> "KeyListResult":
        return KeyListResult(keys=keys, count=len(keys))


@dataclass(frozen=True)
class KeyDeleteResult:
    name: str
    deleted: bool

    @staticmethod
    def from_name(name: str) -> "KeyDeleteResult":
        return KeyDeleteResult(name=name, deleted=True)
