from __future__ import annotations

from crynux_mcp.relay.auth import RelayAuthManager


class FakeRelayApi:
    def __init__(self) -> None:
        self.calls = 0

    def connect_wallet(self, *, address: str, signature: str, timestamp: int):  # type: ignore[no-untyped-def]
        self.calls += 1
        _ = (address, signature, timestamp)
        return {"token": "jwt-new", "expires_at": 2000}


def test_get_valid_session_uses_memory_cache(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    api = FakeRelayApi()
    manager = RelayAuthManager(auth_safety_margin_seconds=10, now_fn=lambda: 1000)

    monkeypatch.setattr(
        manager,
        "_authenticate",
        lambda **kwargs: type(
            "S",
            (),
            {"address": "0x1111111111111111111111111111111111111111", "token": "jwt-a", "expires_at": 2000},
        )(),
    )
    monkeypatch.setattr(manager, "_save_to_keychain", lambda session: None)

    first = manager.get_valid_session(
        address="0x1111111111111111111111111111111111111111",
        key_name=None,
        api=api,
    )
    second = manager.get_valid_session(
        address="0x1111111111111111111111111111111111111111",
        key_name=None,
        api=api,
    )
    assert first.token == "jwt-a"
    assert second.token == "jwt-a"


def test_get_valid_session_uses_keychain_cache(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    api = FakeRelayApi()
    manager = RelayAuthManager(auth_safety_margin_seconds=10, now_fn=lambda: 1000)

    monkeypatch.setattr(manager, "_load_from_keychain", lambda address: type("S", (), {"address": address, "token": "jwt-k", "expires_at": 3000})())
    monkeypatch.setattr(manager, "_authenticate", lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not authenticate")))

    session = manager.get_valid_session(
        address="0x1111111111111111111111111111111111111111",
        key_name=None,
        api=api,
    )
    assert session.token == "jwt-k"


def test_get_valid_session_refreshes_when_expired(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    api = FakeRelayApi()
    manager = RelayAuthManager(auth_safety_margin_seconds=10, now_fn=lambda: 1000)

    monkeypatch.setattr(
        manager,
        "_load_from_keychain",
        lambda address: type("S", (), {"address": address, "token": "jwt-old", "expires_at": 1005})(),
    )
    monkeypatch.setattr(
        manager,
        "_authenticate",
        lambda **kwargs: type(
            "S",
            (),
            {"address": "0x1111111111111111111111111111111111111111", "token": "jwt-new", "expires_at": 3000},
        )(),
    )
    monkeypatch.setattr(manager, "_save_to_keychain", lambda session: None)

    session = manager.get_valid_session(
        address="0x1111111111111111111111111111111111111111",
        key_name=None,
        api=api,
    )
    assert session.token == "jwt-new"


def test_sign_action_rejects_signer_mismatch(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manager = RelayAuthManager(get_private_key_fn=lambda name=None: "0xabc", now_fn=lambda: 1000)
    monkeypatch.setattr(manager, "_address_from_private_key", lambda private_key: "0x2222222222222222222222222222222222222222")

    try:
        manager.sign_action(
            address="0x1111111111111111111111111111111111111111",
            action="Connect Wallet",
            key_name=None,
        )
    except ValueError as exc:
        assert str(exc) == "SIGNER_ADDRESS_MISMATCH: signer private key address does not match the provided address."
    else:
        raise AssertionError("Expected ValueError")
