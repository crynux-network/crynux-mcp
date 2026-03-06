from pathlib import Path

from eth_account import Account

from crynux_mcp.security.key_store import (
    ENV_KEY_NAME,
    add_key,
    create_key,
    delete_key,
    export_key,
    get_private_key,
    list_keys,
    set_default_key,
)


def _mock_keyring(monkeypatch) -> dict[tuple[str, str], str]:  # type: ignore[no-untyped-def]
    storage: dict[tuple[str, str], str] = {}

    def fake_get_password(service: str, account: str):
        return storage.get((service, account))

    def fake_set_password(service: str, account: str, value: str) -> None:
        storage[(service, account)] = value

    def fake_delete_password(service: str, account: str) -> None:
        storage.pop((service, account), None)

    monkeypatch.setattr("crynux_mcp.security.key_store.keyring.get_password", fake_get_password)
    monkeypatch.setattr("crynux_mcp.security.key_store.keyring.set_password", fake_set_password)
    monkeypatch.setattr("crynux_mcp.security.key_store.keyring.delete_password", fake_delete_password)
    return storage


def _mock_index_path(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crynux_mcp.security.key_store.KEY_INDEX_PATH", tmp_path / "keys.json")


def test_add_and_list_keys(monkeypatch, tmp_path: Path) -> None:
    _mock_keyring(monkeypatch)
    _mock_index_path(monkeypatch, tmp_path)

    first = Account.create().key.hex()
    second = Account.create().key.hex()

    first_record = add_key(name="alice", private_key=first)
    second_record = add_key(name="bob", private_key=second)
    keys = list_keys()

    assert first_record["name"] == "alice"
    assert second_record["name"] == "bob"
    assert len(keys) == 2
    assert keys[0]["name"] == "alice"
    assert keys[0]["is_default"] is True


def test_get_private_key_by_name(monkeypatch, tmp_path: Path) -> None:
    _mock_keyring(monkeypatch)
    _mock_index_path(monkeypatch, tmp_path)

    raw = Account.create().key.hex()
    add_key(name="main", private_key=raw)
    assert get_private_key(name="main") == f"0x{raw}"


def test_get_private_key_falls_back_to_env(monkeypatch, tmp_path: Path) -> None:
    _mock_keyring(monkeypatch)
    _mock_index_path(monkeypatch, tmp_path)

    monkeypatch.setenv(ENV_KEY_NAME, "0xenv")
    assert get_private_key() == "0xenv"


def test_create_key_generates_named_key(monkeypatch, tmp_path: Path) -> None:
    _mock_keyring(monkeypatch)
    _mock_index_path(monkeypatch, tmp_path)

    record = create_key("generated")
    keys = list_keys()

    assert record["name"] == "generated"
    assert any(item["name"] == "generated" for item in keys)


def test_delete_key_removes_named_key(monkeypatch, tmp_path: Path) -> None:
    _mock_keyring(monkeypatch)
    _mock_index_path(monkeypatch, tmp_path)

    first = Account.create().key.hex()
    second = Account.create().key.hex()
    add_key(name="alice", private_key=first)
    add_key(name="bob", private_key=second)

    delete_key("alice")
    names = [item["name"] for item in list_keys()]
    assert names == ["bob"]


def test_set_default_key_updates_default(monkeypatch, tmp_path: Path) -> None:
    _mock_keyring(monkeypatch)
    _mock_index_path(monkeypatch, tmp_path)

    first = Account.create().key.hex()
    second = Account.create().key.hex()
    add_key(name="alice", private_key=first)
    add_key(name="bob", private_key=second)

    record = set_default_key("bob")
    keys = list_keys()
    key_map = {item["name"]: item["is_default"] for item in keys}

    assert record["name"] == "bob"
    assert key_map["alice"] is False
    assert key_map["bob"] is True


def test_export_key_writes_private_key_file(monkeypatch, tmp_path: Path) -> None:
    _mock_keyring(monkeypatch)
    _mock_index_path(monkeypatch, tmp_path)

    raw = Account.create().key.hex()
    add_key(name="alice", private_key=raw)
    output = tmp_path / "exports" / "alice.key"

    record = export_key(name="alice", filename=str(output))
    assert output.read_text(encoding="utf-8") == f"0x{raw}"
    assert record["name"] == "alice"
    assert record["filename"] == str(output.resolve())
    assert record["written"] is True


def test_get_private_key_raises_when_missing(monkeypatch, tmp_path: Path) -> None:
    _mock_keyring(monkeypatch)
    _mock_index_path(monkeypatch, tmp_path)
    monkeypatch.delenv(ENV_KEY_NAME, raising=False)

    try:
        get_private_key()
    except ValueError as exc:
        assert "MISSING_PRIVATE_KEY" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_add_key_accepts_hex_key_with_0x_prefix(monkeypatch, tmp_path: Path) -> None:
    storage = _mock_keyring(monkeypatch)
    _mock_index_path(monkeypatch, tmp_path)

    test_key = "0x68bb18155ce073aad5ace00898f12c198597179b274b9dfaaf56bbdd4f144711"
    record = add_key(name="fixture", private_key=test_key)

    assert record["name"] == "fixture"
    assert record["address"] == "0x3D383c0e65E9d0eef397aa7CBE3Ab8bdc1F9C10F"
    assert storage[("crynux-mcp", "key:fixture")] == test_key
