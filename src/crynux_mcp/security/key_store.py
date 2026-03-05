from __future__ import annotations

import json
import os
from getpass import getpass
from pathlib import Path
from typing import Any

from eth_account import Account
import keyring


SERVICE_NAME = "crynux-mcp"
ACCOUNT_NAME = "default-signer"
ENV_KEY_NAME = "CRYNUX_PRIVATE_KEY"
KEY_INDEX_PATH = Path.home() / ".crynux-mcp" / "keys.json"


def _normalize_name(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized:
        raise ValueError("INVALID_KEY_NAME: key name is required.")
    return normalized


def _index_account_name(name: str) -> str:
    return f"key:{name}"


def _ensure_parent_dir() -> None:
    KEY_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_index() -> dict[str, Any]:
    if not KEY_INDEX_PATH.exists():
        return {"default": None, "keys": {}}
    content = KEY_INDEX_PATH.read_text(encoding="utf-8").strip()
    if not content:
        return {"default": None, "keys": {}}
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("INVALID_KEY_INDEX: key index file is corrupted.") from exc
    if not isinstance(data, dict):
        raise ValueError("INVALID_KEY_INDEX: key index structure is invalid.")
    keys = data.get("keys", {})
    if not isinstance(keys, dict):
        raise ValueError("INVALID_KEY_INDEX: key index structure is invalid.")
    default = data.get("default")
    if default is not None and not isinstance(default, str):
        raise ValueError("INVALID_KEY_INDEX: key index structure is invalid.")
    return {"default": default, "keys": keys}


def _save_index(index: dict[str, Any]) -> None:
    _ensure_parent_dir()
    KEY_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=True, indent=2), encoding="utf-8")


def _validate_private_key(raw_key: str) -> tuple[str, str]:
    private_key = (raw_key or "").strip()
    if not private_key:
        raise ValueError("INVALID_PRIVATE_KEY: private key is required.")
    try:
        account = Account.from_key(private_key)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("INVALID_PRIVATE_KEY: private key is invalid.") from exc
    return private_key, account.address


def _set_key(name: str, raw_key: str) -> dict[str, str]:
    key_name = _normalize_name(name)
    private_key, address = _validate_private_key(raw_key)
    keyring.set_password(SERVICE_NAME, _index_account_name(key_name), private_key)

    index = _load_index()
    index["keys"][key_name] = {"address": address}
    if not index.get("default"):
        index["default"] = key_name
    _save_index(index)
    return {"name": key_name, "address": address}


def add_key(name: str, private_key: str) -> dict[str, str]:
    return _set_key(name=name, raw_key=private_key)


def create_key(name: str) -> dict[str, str]:
    key_name = _normalize_name(name)
    account = Account.create()
    return _set_key(name=key_name, raw_key=account.key.hex())


def list_keys() -> list[dict[str, Any]]:
    index = _load_index()
    default_name = index.get("default")
    keys = index.get("keys", {})
    result: list[dict[str, Any]] = []
    for name in sorted(keys.keys()):
        entry = keys[name]
        address = entry.get("address")
        if not isinstance(address, str) or not address:
            continue
        result.append({"name": name, "address": address, "is_default": name == default_name})
    return result


def delete_key(name: str) -> None:
    key_name = _normalize_name(name)
    index = _load_index()
    if key_name not in index["keys"]:
        raise ValueError(f"KEY_NOT_FOUND: key '{key_name}' does not exist.")
    try:
        keyring.delete_password(SERVICE_NAME, _index_account_name(key_name))
    except keyring.errors.PasswordDeleteError:
        pass
    del index["keys"][key_name]
    if index.get("default") == key_name:
        remaining = sorted(index["keys"].keys())
        index["default"] = remaining[0] if remaining else None
    _save_index(index)


def set_default_key(name: str) -> dict[str, Any]:
    key_name = _normalize_name(name)
    index = _load_index()
    keys = index.get("keys", {})
    if key_name not in keys:
        raise ValueError(f"KEY_NOT_FOUND: key '{key_name}' does not exist.")
    index["default"] = key_name
    _save_index(index)
    entry = keys[key_name]
    address = entry.get("address", "")
    return {"name": key_name, "address": address, "is_default": True}


def export_key(name: str, filename: str) -> dict[str, Any]:
    key_name = _normalize_name(name)
    raw_filename = (filename or "").strip()
    if not raw_filename:
        raise ValueError("INVALID_FILENAME: filename is required.")

    key_value = get_private_key(name=key_name)
    path = Path(raw_filename).expanduser()
    if not path.is_absolute():
        path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key_value, encoding="utf-8")
    if os.name != "nt":
        os.chmod(path, 0o600)
    return {"name": key_name, "filename": str(path), "written": True}


def get_private_key(name: str | None = None) -> str:
    index = _load_index()
    key_name = _normalize_name(name) if name is not None else index.get("default")
    if isinstance(key_name, str) and key_name:
        stored = (keyring.get_password(SERVICE_NAME, _index_account_name(key_name)) or "").strip()
        if stored:
            return stored
        raise ValueError(f"MISSING_PRIVATE_KEY: key '{key_name}' is not available in system keychain.")

    # Backward compatibility for old single-key storage.
    legacy_stored = (keyring.get_password(SERVICE_NAME, ACCOUNT_NAME) or "").strip()
    if legacy_stored:
        return legacy_stored

    fallback = os.getenv(ENV_KEY_NAME, "").strip()
    if fallback:
        return fallback

    raise ValueError(
        "MISSING_PRIVATE_KEY: no signer key found. Use 'crynux-mcp key add --name <name>', "
        "'crynux-mcp key create --name <name>', or set CRYNUX_PRIVATE_KEY."
    )


def has_private_key() -> bool:
    try:
        return bool(get_private_key())
    except ValueError:
        return False


def prompt_and_add_key(name: str) -> dict[str, str]:
    private_key = getpass("Enter signer private key (input hidden): ").strip()
    return add_key(name=name, private_key=private_key)
