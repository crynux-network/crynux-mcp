from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Callable, Protocol

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import is_address, to_checksum_address
import keyring

from crynux_mcp.relay.models import RelayAuthSession
from crynux_mcp.security.key_store import get_private_key as get_local_private_key


TOKEN_SERVICE_NAME = "crynux-mcp-relay"


class RelayConnectWalletApi(Protocol):
    def connect_wallet(self, *, address: str, signature: str, timestamp: int) -> dict[str, str | int]:
        ...


def build_relay_message(*, action: str, address: str, timestamp: int) -> str:
    return f"Crynux Relay\nAction: {action}\nAddress: {address}\nTimestamp: {timestamp}"


class RelayAuthManager:
    def __init__(
        self,
        *,
        auth_safety_margin_seconds: int = 30,
        get_private_key_fn: Callable[[str | None], str] = get_local_private_key,
        now_fn: Callable[[], int] = lambda: int(time.time()),  # noqa: E731
    ) -> None:
        self._auth_safety_margin_seconds = max(0, int(auth_safety_margin_seconds))
        self._get_private_key = get_private_key_fn
        self._now = now_fn
        self._memory_sessions: dict[str, RelayAuthSession] = {}

    def get_valid_session(
        self,
        *,
        address: str,
        key_name: str | None,
        api: RelayConnectWalletApi,
        force_refresh: bool = False,
    ) -> RelayAuthSession:
        normalized_address = self._normalize_address(address)
        if not force_refresh:
            memory_hit = self._memory_sessions.get(normalized_address)
            if memory_hit and self._is_valid(memory_hit):
                return memory_hit

            keychain_hit = self._load_from_keychain(normalized_address)
            if keychain_hit and self._is_valid(keychain_hit):
                self._memory_sessions[normalized_address] = keychain_hit
                return keychain_hit

        session = self._authenticate(address=normalized_address, key_name=key_name, api=api)
        self._memory_sessions[normalized_address] = session
        self._save_to_keychain(session)
        return session

    def sign_action(
        self,
        *,
        address: str,
        action: str,
        key_name: str | None = None,
        timestamp: int | None = None,
    ) -> tuple[int, str]:
        normalized_address = self._normalize_address(address)
        private_key = self._get_private_key(key_name)
        signer_address = self._address_from_private_key(private_key)
        if signer_address != normalized_address:
            raise ValueError(
                "SIGNER_ADDRESS_MISMATCH: signer private key address does not match the provided address."
            )
        signed_at = int(timestamp if timestamp is not None else self._now())
        message = build_relay_message(action=action, address=normalized_address, timestamp=signed_at)
        encoded = encode_defunct(text=message)
        signature = Account.sign_message(encoded, private_key=private_key).signature.hex()
        return signed_at, signature

    def _authenticate(self, *, address: str, key_name: str | None, api: RelayConnectWalletApi) -> RelayAuthSession:
        timestamp, signature = self.sign_action(address=address, action="Connect Wallet", key_name=key_name)
        response = api.connect_wallet(address=address, signature=signature, timestamp=timestamp)
        token = str(response.get("token", "")).strip()
        expires_at = int(response.get("expires_at", 0))
        if not token:
            raise ValueError("INVALID_RELAY_AUTH_RESPONSE: missing token in relay auth response.")
        if expires_at <= 0:
            raise ValueError("INVALID_RELAY_AUTH_RESPONSE: missing expires_at in relay auth response.")
        return RelayAuthSession(address=address, token=token, expires_at=expires_at)

    def _is_valid(self, session: RelayAuthSession) -> bool:
        return session.expires_at > (self._now() + self._auth_safety_margin_seconds)

    def _token_account_name(self, address: str) -> str:
        return f"token:{address}"

    def _load_from_keychain(self, address: str) -> RelayAuthSession | None:
        raw = (keyring.get_password(TOKEN_SERVICE_NAME, self._token_account_name(address)) or "").strip()
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        session = RelayAuthSession.from_dict(payload)
        if session.address != address:
            return None
        if not session.token:
            return None
        return session

    def _save_to_keychain(self, session: RelayAuthSession) -> None:
        # Keychain write failure should not block API calls.
        try:
            keyring.set_password(
                TOKEN_SERVICE_NAME,
                self._token_account_name(session.address),
                json.dumps(asdict(session), ensure_ascii=True),
            )
        except Exception:  # noqa: BLE001
            return

    def _normalize_address(self, address: str) -> str:
        candidate = (address or "").strip()
        if not candidate:
            raise ValueError("INVALID_ADDRESS: address is required.")
        if not is_address(candidate):
            raise ValueError("INVALID_ADDRESS: address must be a valid EVM address.")
        return to_checksum_address(candidate)

    def _address_from_private_key(self, private_key: str) -> str:
        try:
            account = Account.from_key(private_key)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("INVALID_PRIVATE_KEY: private key is invalid.") from exc
        return to_checksum_address(account.address)
