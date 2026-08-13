from crynux_mcp.blockchain.schemas import normalize_unit, parse_amount_to_wei, parse_non_negative_amount_to_wei
from crynux_mcp.config.loader import load_chain_registry
from crynux_mcp.relay.config import assert_relay_env_matches_network, load_relay_config


def test_registry_loads_default_and_networks() -> None:
    registry = load_chain_registry()
    assert registry.default_network == "crynux-on-base"
    assert "crynux-on-base" in registry.networks
    assert "crynux-on-base-sepolia" in registry.networks
    assert registry.resolve(None).network_key == "crynux-on-base"
    assert registry.resolve("crynux-on-base").network_kind == "mainnet"
    assert registry.resolve("crynux-on-base-sepolia").network_kind == "testnet"
    assert "credits" not in registry.resolve("crynux-on-base").contracts


def test_relay_config_loads_environments() -> None:
    config = load_relay_config()
    assert config.default_env == "production"
    assert set(config.environments) == {"production", "staging"}
    assert config.get_base_url("production") == "https://relay.crynux.io"
    assert config.get_base_url("staging") == "https://staging.relay.crynux.io"
    assert (
        config.get_deposit_address("production")
        == "0x95dAd4af9aCaDEaf1704d3C980e7f571A9c5C5a0"
    )
    assert (
        config.get_deposit_address("staging")
        == "0x7bB0A0582893c09ED48397BFACDdbbd478eB4839"
    )
    assert (
        config.get_base_url("staging", relay_base_url="https://relay.custom.test")
        == "https://relay.custom.test"
    )
    assert (
        config.get_deposit_address("staging")
        == "0x7bB0A0582893c09ED48397BFACDdbbd478eB4839"
    )


def test_assert_relay_env_matches_network_accepts_valid_pairs() -> None:
    registry = load_chain_registry()
    assert_relay_env_matches_network("production", registry.resolve("crynux-on-base"))
    assert_relay_env_matches_network("staging", registry.resolve("crynux-on-base-sepolia"))


def test_assert_relay_env_matches_network_rejects_mismatched_pairs() -> None:
    registry = load_chain_registry()
    try:
        assert_relay_env_matches_network("staging", registry.resolve("crynux-on-base"))
    except ValueError as exc:
        assert str(exc).startswith("INVALID_RELAY_NETWORK_PAIRING:")
    else:
        raise AssertionError("Expected ValueError")

    try:
        assert_relay_env_matches_network(
            "production",
            registry.resolve("crynux-on-base-sepolia"),
        )
    except ValueError as exc:
        assert str(exc).startswith("INVALID_RELAY_NETWORK_PAIRING:")
    else:
        raise AssertionError("Expected ValueError")


def test_normalize_unit_defaults_to_ether() -> None:
    assert normalize_unit(None) == "ether"
    assert normalize_unit("wei") == "wei"
    assert normalize_unit("ETHER") == "ether"


def test_parse_amount_to_wei_for_ether() -> None:
    assert parse_amount_to_wei("1", "ether") == 10**18
    assert parse_amount_to_wei("0.5", "ether") == 5 * 10**17


def test_parse_amount_to_wei_for_wei() -> None:
    assert parse_amount_to_wei("42", "wei") == 42


def test_parse_non_negative_amount_to_wei_allows_zero() -> None:
    assert parse_non_negative_amount_to_wei("0", "wei") == 0
    assert parse_non_negative_amount_to_wei("0", "ether") == 0
