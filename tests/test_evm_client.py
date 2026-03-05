from crynux_mcp.blockchain.schemas import normalize_unit, parse_amount_to_wei
from crynux_mcp.config.loader import load_chain_registry


def test_registry_loads_default_and_networks() -> None:
    registry = load_chain_registry()
    assert registry.default_network == "dymension"
    assert "dymension" in registry.networks
    assert "near" in registry.networks
    assert registry.resolve(None).network_key == "dymension"


def test_normalize_unit_defaults_to_ether() -> None:
    assert normalize_unit(None) == "ether"
    assert normalize_unit("wei") == "wei"
    assert normalize_unit("ETHER") == "ether"


def test_parse_amount_to_wei_for_ether() -> None:
    assert parse_amount_to_wei("1", "ether") == 10**18
    assert parse_amount_to_wei("0.5", "ether") == 5 * 10**17


def test_parse_amount_to_wei_for_wei() -> None:
    assert parse_amount_to_wei("42", "wei") == 42
