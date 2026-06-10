"""hak-saucerswap-plugin: Hedera Agent Kit (Python) plugin for the SaucerSwap DEX."""

from hedera_agent_kit.shared.plugin import Plugin

from .config import SaucerSwapConfig, resolve_saucerswap_config
from .networks import (
    NETWORK_DEFAULTS,
    SAUCERSWAP_MAINNET,
    SAUCERSWAP_TESTNET,
    SaucerSwapNetworkDefaults,
)
from .tools import (
    SAUCERSWAP_ADD_LIQUIDITY_TOOL,
    SAUCERSWAP_GET_FARMS_TOOL,
    SAUCERSWAP_GET_POOLS_TOOL,
    SAUCERSWAP_GET_SWAP_QUOTE_TOOL,
    SAUCERSWAP_REMOVE_LIQUIDITY_TOOL,
    SAUCERSWAP_SWAP_TOKENS_TOOL,
    AddLiquidityTool,
    FarmsTool,
    PoolsTool,
    QuoteTool,
    RemoveLiquidityTool,
    SwapTool,
)

__version__ = "0.1.0"

saucerswap_plugin_tool_names = {
    "SAUCERSWAP_GET_SWAP_QUOTE_TOOL": SAUCERSWAP_GET_SWAP_QUOTE_TOOL,
    "SAUCERSWAP_SWAP_TOKENS_TOOL": SAUCERSWAP_SWAP_TOKENS_TOOL,
    "SAUCERSWAP_GET_POOLS_TOOL": SAUCERSWAP_GET_POOLS_TOOL,
    "SAUCERSWAP_ADD_LIQUIDITY_TOOL": SAUCERSWAP_ADD_LIQUIDITY_TOOL,
    "SAUCERSWAP_REMOVE_LIQUIDITY_TOOL": SAUCERSWAP_REMOVE_LIQUIDITY_TOOL,
    "SAUCERSWAP_GET_FARMS_TOOL": SAUCERSWAP_GET_FARMS_TOOL,
}

saucerswap_plugin = Plugin(
    name="saucerswap",
    version=__version__,
    description=(
        "Integration with SaucerSwap DEX for token swaps, liquidity provision, "
        "and yield farming"
    ),
    tools=lambda context: [
        SwapTool(context),
        QuoteTool(context),
        PoolsTool(context),
        AddLiquidityTool(context),
        RemoveLiquidityTool(context),
        FarmsTool(context),
    ],
)

__all__ = [
    "saucerswap_plugin",
    "saucerswap_plugin_tool_names",
    "SaucerSwapConfig",
    "resolve_saucerswap_config",
    "SaucerSwapNetworkDefaults",
    "SAUCERSWAP_MAINNET",
    "SAUCERSWAP_TESTNET",
    "NETWORK_DEFAULTS",
    "SwapTool",
    "QuoteTool",
    "PoolsTool",
    "AddLiquidityTool",
    "RemoveLiquidityTool",
    "FarmsTool",
]
