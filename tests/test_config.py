from hak_saucerswap_plugin.config import resolve_saucerswap_config
from hak_saucerswap_plugin.networks import SAUCERSWAP_MAINNET, SAUCERSWAP_TESTNET


class FakeContext:
    pass


def _clear_env(monkeypatch):
    for var in (
        "SAUCERSWAP_NETWORK",
        "SAUCERSWAP_BASE_URL",
        "SAUCERSWAP_API_KEY",
        "SAUCERSWAP_TOKEN_ALIASES",
        "SAUCERSWAP_DEFAULT_POOL_VERSION",
        "SAUCERSWAP_ROUTER_CONTRACT_ID",
        "SAUCERSWAP_ROUTER_V2_CONTRACT_ID",
        "SAUCERSWAP_WRAPPED_HBAR_TOKEN_ID",
        "SAUCERSWAP_GAS_LIMIT",
        "SAUCERSWAP_DEADLINE_MINUTES",
        "SAUCERSWAP_TIMEOUT_SECONDS",
        "SAUCERSWAP_RETRIES",
    ):
        monkeypatch.delenv(var, raising=False)


def test_defaults(monkeypatch):
    _clear_env(monkeypatch)
    config = resolve_saucerswap_config(None)
    assert config.base_url == "https://api.saucerswap.finance"
    assert config.retries == 2
    assert config.default_pool_version == "v2"
    assert config.router_contract_id is None


def test_mainnet_network_defaults(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SAUCERSWAP_NETWORK", "mainnet")
    config = resolve_saucerswap_config(None)
    assert config.router_contract_id == SAUCERSWAP_MAINNET.router_contract_id
    assert config.wrapped_hbar_token_id == SAUCERSWAP_MAINNET.wrapped_hbar_token_id
    assert config.token_aliases["SAUCE"] == "0.0.731861"


def test_context_config_overrides_env(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SAUCERSWAP_NETWORK", "mainnet")
    context = FakeContext()
    context.saucerswap = {
        "network": "testnet",
        "gas_limit": 3_000_000,
        "token_aliases": {"FOO": "0.0.999"},
    }
    config = resolve_saucerswap_config(context)
    assert config.router_contract_id == SAUCERSWAP_TESTNET.router_contract_id
    assert config.gas_limit == 3_000_000
    assert config.token_aliases["FOO"] == "0.0.999"
    assert config.token_aliases["SAUCE"] == SAUCERSWAP_TESTNET.token_aliases["SAUCE"]


def test_env_aliases_and_api_key(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SAUCERSWAP_TOKEN_ALIASES", '{"BAR": "0.0.555"}')
    monkeypatch.setenv("SAUCERSWAP_API_KEY", "secret")
    config = resolve_saucerswap_config(None)
    assert config.token_aliases == {"BAR": "0.0.555"}
    assert config.api_key == "secret"


def test_invalid_env_values_fall_back(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SAUCERSWAP_TOKEN_ALIASES", "not-json")
    monkeypatch.setenv("SAUCERSWAP_GAS_LIMIT", "not-a-number")
    monkeypatch.setenv("SAUCERSWAP_NETWORK", "invalid")
    config = resolve_saucerswap_config(None)
    assert config.token_aliases == {}
    assert config.gas_limit == 2_000_000
    assert config.network is None
