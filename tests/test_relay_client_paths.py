from crynux_mcp.relay.client import RelayApiClient


def test_list_deposits_uses_relay_account_path(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_request_json(self, **kwargs):  # type: ignore[no-untyped-def]
        _ = self
        captured.update(kwargs)
        return {"total": 0, "deposit_records": []}

    monkeypatch.setattr(RelayApiClient, "_request_json", fake_request_json)
    client = RelayApiClient(base_url="http://127.0.0.1:8080", timeout_seconds=10)

    client.list_deposits(
        address="0x1111111111111111111111111111111111111111",
        page=1,
        page_size=10,
        token="jwt-abc",
    )

    assert captured["path"] == "/v1/relay_account/0x1111111111111111111111111111111111111111/deposit/list"


def test_list_withdraws_uses_relay_account_path(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_request_json(self, **kwargs):  # type: ignore[no-untyped-def]
        _ = self
        captured.update(kwargs)
        return {"total": 0, "withdraw_records": []}

    monkeypatch.setattr(RelayApiClient, "_request_json", fake_request_json)
    client = RelayApiClient(base_url="http://127.0.0.1:8080", timeout_seconds=10)

    client.list_withdraws(
        address="0x1111111111111111111111111111111111111111",
        page=1,
        page_size=10,
        token="jwt-abc",
    )

    assert captured["path"] == "/v1/relay_account/0x1111111111111111111111111111111111111111/withdraw/list"
