"""Official SaucerSwap contract addresses per Hedera network.

Source: https://docs.saucerswap.finance/developerx/contract-deployments
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SaucerSwapNetworkDefaults:
    router_contract_id: str
    router_v2_contract_id: str
    wrapped_hbar_token_id: str
    token_aliases: dict[str, str] = field(default_factory=dict)


SAUCERSWAP_MAINNET = SaucerSwapNetworkDefaults(
    router_contract_id="0.0.3045981",
    router_v2_contract_id="0.0.3949434",
    wrapped_hbar_token_id="0.0.1456986",
    token_aliases={
        "SAUCE": "0.0.731861",
        "XSAUCE": "0.0.1460200",
    },
)

SAUCERSWAP_TESTNET = SaucerSwapNetworkDefaults(
    router_contract_id="0.0.19264",
    router_v2_contract_id="0.0.1414040",
    wrapped_hbar_token_id="0.0.15058",
    token_aliases={
        "SAUCE": "0.0.1183558",
        "XSAUCE": "0.0.1418651",
    },
)

NETWORK_DEFAULTS: dict[str, SaucerSwapNetworkDefaults] = {
    "mainnet": SAUCERSWAP_MAINNET,
    "testnet": SAUCERSWAP_TESTNET,
}
