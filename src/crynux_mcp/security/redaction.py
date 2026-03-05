from __future__ import annotations

from typing import Any


SECRET_KEYS = {"private_key", "mnemonic", "seed", "password", "secret"}


def redact_secrets(payload: Any) -> Any:
    if isinstance(payload, dict):
        cleaned: dict[str, Any] = {}
        for key, value in payload.items():
            if key.lower() in SECRET_KEYS:
                cleaned[key] = "***REDACTED***"
            else:
                cleaned[key] = redact_secrets(value)
        return cleaned
    if isinstance(payload, list):
        return [redact_secrets(item) for item in payload]
    return payload


def sanitize_error_message(message: str) -> str:
    lowered = message.lower()
    if "private key" in lowered:
        return "INVALID_PRIVATE_KEY: private key is invalid."
    return message
