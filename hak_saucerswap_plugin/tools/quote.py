from __future__ import annotations

import json
from typing import Any

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hiero_sdk_python import Client
from pydantic import BaseModel, Field

from ..config import resolve_saucerswap_config
from ..utils.amm import apply_slippage_to_amount, calculate_price_impact
from ..utils.quote import normalize_swap_quote
from ..utils.tokens import normalize_token_alias
from .common import get_api_client

SAUCERSWAP_GET_SWAP_QUOTE_TOOL = "saucerswap_get_swap_quote"


class QuoteParameters(BaseModel):
    from_token: str = Field(
        description=(
            "Token to swap from: a token ID like '0.0.731861', a symbol like 'SAUCE', or 'HBAR'"
        )
    )
    to_token: str = Field(description="Token to swap to (token ID or symbol)")
    amount: str = Field(description="Amount to swap, in decimal format (e.g. '10.5')")
    slippage_tolerance: float = Field(
        default=0.5, description="Maximum slippage tolerance percentage (default 0.5)"
    )


class QuoteTool(BaseToolV2):
    """Read-only tool returning a SaucerSwap swap quote."""

    def __init__(self, context: Context | None = None):
        self.method = SAUCERSWAP_GET_SWAP_QUOTE_TOOL
        self.name = "SaucerSwap Get Swap Quote"
        self.description = (
            "Get a price quote for swapping tokens on SaucerSwap. "
            "Returns the expected output amount, minimum output after slippage, "
            "estimated price impact, and the swap route. Read-only: no transaction is executed."
        )
        self.parameters = QuoteParameters

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> QuoteParameters:
        if isinstance(params, QuoteParameters):
            return params
        return QuoteParameters.model_validate(params)

    async def core_action(
        self, normalized_params: QuoteParameters, context: Context, client: Client
    ) -> ToolResponse:
        config = resolve_saucerswap_config(context)
        api = get_api_client(context, config)
        args = normalized_params

        from_token = normalize_token_alias(args.from_token, config)
        to_token = normalize_token_alias(args.to_token, config)
        from_token_id = await api.resolve_token_id(from_token)
        to_token_id = await api.resolve_token_id(to_token)

        raw_quote = await api.get_swap_quote(
            from_token=from_token_id, to_token=to_token_id, amount=args.amount
        )
        quote = normalize_swap_quote(raw_quote, args.amount)

        if quote["price_impact"] is None:
            pool = await api.get_pool_by_tokens(
                from_token_id, to_token_id, config.default_pool_version
            )
            if pool and raw_quote.get("amountIn") and raw_quote.get("amountOut"):
                is_a_to_b = pool["tokenA"]["id"] == from_token_id
                reserve_in = pool["tokenReserveA"] if is_a_to_b else pool["tokenReserveB"]
                reserve_out = pool["tokenReserveB"] if is_a_to_b else pool["tokenReserveA"]
                quote["price_impact"] = calculate_price_impact(
                    str(raw_quote["amountIn"]),
                    str(raw_quote["amountOut"]),
                    str(reserve_in),
                    str(reserve_out),
                )

        expected = quote["expected_output"]
        if "." in expected:
            try:
                min_output: str | None = str(
                    float(expected) * (1 - args.slippage_tolerance / 100)
                )
            except ValueError:
                min_output = None
        else:
            min_output = apply_slippage_to_amount(expected, args.slippage_tolerance)

        extra = {"success": True, "quote": quote, "min_output": min_output}
        return ToolResponse(
            human_message=json.dumps(
                {
                    "expected_output": quote["expected_output"],
                    "min_output": min_output,
                    "price_impact": quote["price_impact"],
                    "route": quote["route"],
                },
                default=str,
            ),
            extra=extra,
        )

    async def should_secondary_action(self, core_result: Any, context: Context) -> bool:
        return False


quote_tool = QuoteTool
