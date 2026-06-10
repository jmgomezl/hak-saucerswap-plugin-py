"""Configuration resolution for the SaucerSwap plugin.

Precedence (highest first): context-attached config -> environment variables
-> network defaults -> built-in defaults. Mirrors the TypeScript plugin's
`resolveSaucerSwapConfig`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from .networks import NETWORK_DEFAULTS

PoolVersion = str  # "v1" | "v2"

DEFAULT_BASE_URL = "https://api.saucerswap.finance"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRIES = 2
DEFAULT_POOL_VERSION: PoolVersion = "v2"
DEFAULT_GAS_LIMIT = 2_000_000
DEFAULT_DEADLINE_MINUTES = 20


@dataclass
class SaucerSwapConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    retries: int = DEFAULT_RETRIES
    api_key: str | None = None
    network: str | None = None
    router_contract_id: str | None = None
    router_v2_contract_id: str | None = None
    wrapped_hbar_token_id: str | None = None
    token_aliases: dict[str, str] = field(default_factory=dict)
    default_pool_version: PoolVersion = DEFAULT_POOL_VERSION
    gas_limit: int = DEFAULT_GAS_LIMIT
    deadline_minutes: int = DEFAULT_DEADLINE_MINUTES


def _to_number(value: str | None, fallback: float) -> float:
    if not value:
        return fallback
    try:
        return float(value)
    except ValueError:
        return fallback


def _to_int(value: str | None, fallback: int) -> int:
    if not value:
        return fallback
    try:
        return int(float(value))
    except ValueError:
        return fallback


def _read_token_aliases(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return {str(k): str(v) for k, v in parsed.items()}
    return {}


def _read_pool_version(value: str | None) -> PoolVersion | None:
    return value if value in ("v1", "v2") else None


def _read_network(value: str | None) -> str | None:
    return value if value in ("mainnet", "testnet") else None


def _read_context_config(context: Any) -> dict[str, Any]:
    """Extract plugin config attached to the runtime context.

    Supports a `saucerswap` attribute (or key) on the context holding either a
    dict or a SaucerSwapConfig-like object.
    """
    if context is None:
        return {}
    raw = None
    if isinstance(context, dict):
        raw = context.get("saucerswap")
    else:
        raw = getattr(context, "saucerswap", None)
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, SaucerSwapConfig):
        return {k: v for k, v in vars(raw).items()}
    return {k: v for k, v in vars(raw).items() if not k.startswith("_")}


def resolve_saucerswap_config(context: Any = None) -> SaucerSwapConfig:
    ctx = _read_context_config(context)

    network = _read_network(ctx.get("network")) or _read_network(
        os.environ.get("SAUCERSWAP_NETWORK")
    )
    defaults = NETWORK_DEFAULTS.get(network) if network else None

    env_aliases = _read_token_aliases(os.environ.get("SAUCERSWAP_TOKEN_ALIASES"))
    env_pool_version = _read_pool_version(os.environ.get("SAUCERSWAP_DEFAULT_POOL_VERSION"))

    token_aliases: dict[str, str] = {}
    if defaults:
        token_aliases.update(defaults.token_aliases)
    token_aliases.update(env_aliases)
    token_aliases.update(ctx.get("token_aliases") or {})

    return SaucerSwapConfig(
        base_url=ctx.get("base_url")
        or os.environ.get("SAUCERSWAP_BASE_URL")
        or DEFAULT_BASE_URL,
        timeout_seconds=ctx.get("timeout_seconds")
        or _to_number(os.environ.get("SAUCERSWAP_TIMEOUT_SECONDS"), DEFAULT_TIMEOUT_SECONDS),
        retries=ctx.get("retries")
        if ctx.get("retries") is not None
        else _to_int(os.environ.get("SAUCERSWAP_RETRIES"), DEFAULT_RETRIES),
        api_key=ctx.get("api_key") or os.environ.get("SAUCERSWAP_API_KEY"),
        network=network,
        router_contract_id=ctx.get("router_contract_id")
        or os.environ.get("SAUCERSWAP_ROUTER_CONTRACT_ID")
        or (defaults.router_contract_id if defaults else None),
        router_v2_contract_id=ctx.get("router_v2_contract_id")
        or os.environ.get("SAUCERSWAP_ROUTER_V2_CONTRACT_ID")
        or (defaults.router_v2_contract_id if defaults else None),
        wrapped_hbar_token_id=ctx.get("wrapped_hbar_token_id")
        or os.environ.get("SAUCERSWAP_WRAPPED_HBAR_TOKEN_ID")
        or (defaults.wrapped_hbar_token_id if defaults else None),
        token_aliases=token_aliases,
        default_pool_version=ctx.get("default_pool_version")
        or env_pool_version
        or DEFAULT_POOL_VERSION,
        gas_limit=ctx.get("gas_limit")
        or _to_int(os.environ.get("SAUCERSWAP_GAS_LIMIT"), DEFAULT_GAS_LIMIT),
        deadline_minutes=ctx.get("deadline_minutes")
        or _to_int(os.environ.get("SAUCERSWAP_DEADLINE_MINUTES"), DEFAULT_DEADLINE_MINUTES),
    )
