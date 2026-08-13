from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address

from crynux_mcp.security.signing import sign_message
from crynux_mcp.server import sign_message as sign_message_tool


def test_sign_message_utf8_roundtrip() -> None:
    account = Account.create()
    message = "hello crynux"
    result = sign_message(private_key=account.key.hex(), message=message, encoding="utf8")

    assert result.address == to_checksum_address(account.address)
    assert result.message == message
    assert result.message_encoding == "utf8"
    assert result.signature.startswith("0x")

    recovered = Account.recover_message(encode_defunct(text=message), signature=result.signature)
    assert to_checksum_address(recovered) == result.address


def test_sign_message_hex_and_hash() -> None:
    account = Account.create()
    payload_hex = "0xdeadbeef"
    hex_result = sign_message(private_key=account.key.hex(), message=payload_hex, encoding="hex")
    recovered_hex = Account.recover_message(
        encode_defunct(hexstr=payload_hex),
        signature=hex_result.signature,
    )
    assert to_checksum_address(recovered_hex) == hex_result.address

    digest = "0x" + ("11" * 32)
    hash_result = sign_message(private_key=account.key.hex(), message=digest, encoding="hash")
    assert hash_result.message_encoding == "hash"
    assert hash_result.signature.startswith("0x")


def test_sign_message_tool_never_returns_private_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    account = Account.create()
    monkeypatch.setattr("crynux_mcp.server.get_private_key", lambda name=None: account.key.hex())

    payload = sign_message_tool(message="Connect Wallet", key_name="main")
    assert payload["address"] == to_checksum_address(account.address)
    assert payload["signature"].startswith("0x")
    assert "private_key" not in payload
    assert account.key.hex() not in str(payload)


def test_sign_message_rejects_empty_message() -> None:
    account = Account.create()
    try:
        sign_message(private_key=account.key.hex(), message="")
    except ValueError as exc:
        assert str(exc).startswith("INVALID_MESSAGE:")
    else:
        raise AssertionError("Expected ValueError")
