from __future__ import annotations

from typing import Literal

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount
from eth_utils import to_checksum_address

from crynux_mcp.security.schemas import SignMessageResult

MessageEncoding = Literal["utf8", "hex", "hash"]
VALID_MESSAGE_ENCODINGS = frozenset({"utf8", "hex", "hash"})
MAX_MESSAGE_CHARS = 100_000


def normalize_message_encoding(encoding: str | None) -> MessageEncoding:
    if encoding is None:
        return "utf8"
    normalized = encoding.strip().lower()
    if normalized not in VALID_MESSAGE_ENCODINGS:
        raise ValueError(
            "INVALID_MESSAGE_ENCODING: encoding must be 'utf8', 'hex', or 'hash'."
        )
    return normalized  # type: ignore[return-type]


def sign_message(
    *,
    private_key: str,
    message: str,
    encoding: str | None = "utf8",
) -> SignMessageResult:
    raw_message = message if isinstance(message, str) else ""
    if not raw_message:
        raise ValueError("INVALID_MESSAGE: message is required.")
    if len(raw_message) > MAX_MESSAGE_CHARS:
        raise ValueError(
            f"INVALID_MESSAGE: message must be at most {MAX_MESSAGE_CHARS} characters."
        )

    message_encoding = normalize_message_encoding(encoding)
    account = _account_from_private_key(private_key)

    if message_encoding == "utf8":
        signed = Account.sign_message(encode_defunct(text=raw_message), private_key=private_key)
    elif message_encoding == "hex":
        signed = Account.sign_message(
            encode_defunct(hexstr=_normalize_hex(raw_message)),
            private_key=private_key,
        )
    else:
        message_hash = bytes.fromhex(_normalize_hex(raw_message)[2:])
        if len(message_hash) != 32:
            raise ValueError("INVALID_MESSAGE: hash encoding requires a 32-byte hex digest.")
        signed = Account.unsafe_sign_hash(message_hash, private_key=private_key)

    return SignMessageResult(
        address=to_checksum_address(account.address),
        message=raw_message,
        message_encoding=message_encoding,
        signature=_normalize_signature_hex(signed.signature.hex()),
    )


def _account_from_private_key(private_key: str) -> LocalAccount:
    raw = (private_key or "").strip()
    if not raw:
        raise ValueError("INVALID_PRIVATE_KEY: private key is required.")
    try:
        return Account.from_key(raw)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("INVALID_PRIVATE_KEY: private key is invalid.") from exc


def _normalize_hex(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("INVALID_MESSAGE: hex message is required.")
    if raw.lower().startswith("0x"):
        body = raw[2:]
    else:
        body = raw
    if not body or len(body) % 2 != 0:
        raise ValueError("INVALID_MESSAGE: hex message must be even-length hex.")
    try:
        bytes.fromhex(body)
    except ValueError as exc:
        raise ValueError("INVALID_MESSAGE: hex message must be valid hexadecimal.") from exc
    return f"0x{body}"


def _normalize_signature_hex(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("INVALID_SIGNATURE: signature is empty.")
    if raw.lower().startswith("0x"):
        return f"0x{raw[2:]}"
    return f"0x{raw}"
