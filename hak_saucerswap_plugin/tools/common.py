"""Shared helpers used by the SaucerSwap tools."""

from __future__ import annotations

import time
from typing import Any

from ..api.client import SaucerSwapClient, create_saucerswap_client
from ..config import SaucerSwapConfig


def get_api_client(context: Any, config: SaucerSwapConfig) -> SaucerSwapClient:
    """Return an injected SaucerSwap client from context, or build one from config."""
    injected = (
        context.get("saucerswap_client")
        if isinstance(context, dict)
        else getattr(context, "saucerswap_client", None)
    )
    return injected or create_saucerswap_client(config)


def get_operator_account_id(client: Any, context: Any) -> str | None:
    """Resolve the acting account: the client operator or the context account."""
    operator = getattr(client, "operator_account_id", None)
    if operator is not None:
        return str(operator)
    if isinstance(context, dict):
        account_id = context.get("account_id")
    else:
        account_id = getattr(context, "account_id", None)
    return str(account_id) if account_id else None


def resolve_deadline(deadline_input: float | None, default_minutes: int) -> int:
    """Interpret a deadline as minutes-from-now or an absolute unix timestamp."""
    now = int(time.time())
    if not deadline_input:
        return now + default_minutes * 60
    if deadline_input > now + 60:
        return int(deadline_input)
    return now + round(deadline_input) * 60


def resolve_router_contract(config: SaucerSwapConfig) -> str:
    if config.default_pool_version == "v2":
        router = config.router_v2_contract_id or config.router_contract_id
    else:
        router = config.router_contract_id or config.router_v2_contract_id
    if not router:
        raise ValueError("Missing SaucerSwap router contract ID configuration.")
    return router
