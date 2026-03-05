from crynux_mcp.server import create_key, delete_key, export_key, list_keys, set_default_key


def test_create_key_tool_returns_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crynux_mcp.server.create_local_key", lambda name: {"name": name, "address": "0xabc"})
    payload = create_key("alice")
    assert payload["name"] == "alice"
    assert payload["address"] == "0xabc"
    assert "text" in payload


def test_list_keys_tool_returns_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server.list_local_keys",
        lambda: [{"name": "alice", "address": "0xabc", "is_default": True}],
    )
    payload = list_keys()
    assert payload["count"] == 1
    assert payload["keys"][0]["name"] == "alice"
    assert "text" in payload


def test_delete_key_tool_returns_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crynux_mcp.server.delete_local_key", lambda name: None)
    payload = delete_key("alice")
    assert payload["name"] == "alice"
    assert payload["deleted"] is True
    assert "text" in payload


def test_set_default_key_tool_returns_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server.set_default_local_key",
        lambda name: {"name": name, "address": "0xabc", "is_default": True},
    )
    payload = set_default_key("alice")
    assert payload["name"] == "alice"
    assert payload["is_default"] is True
    assert "text" in payload


def test_export_key_tool_returns_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "crynux_mcp.server.export_local_key",
        lambda name, filename: {"name": name, "filename": filename, "written": True},
    )
    payload = export_key("alice", "/tmp/alice.key")
    assert payload["name"] == "alice"
    assert payload["filename"] == "/tmp/alice.key"
    assert payload["written"] is True
    assert "text" in payload
