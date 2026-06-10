from __future__ import annotations

import json
from typing import Any, Literal

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hiero_sdk_python import Client
from pydantic import BaseModel, Field

from ..config import resolve_saucerswap_config
from ..utils.tokens import normalize_token_alias
from .common import get_api_client

SAUCERSWAP_GET_POOLS_TOOL = "saucerswap_get_pools"


class PoolsParameters(BaseModel):
    token_a: str | None = Field(default=None, description="First token ID or symbol to filter by")
    token_b: str | None = Field(default=None, description="Second token ID or symbol to filter by")
    version: Literal["v1", "v2"] | None = Field(
        default=None, description="Pool version ('v1' or 'v2'); defaults to the configured version"
    )
    limit: int | None = Field(
        default=None, gt=0, description="Maximum number of pools to return"
    )


class PoolsTool(BaseToolV2):
    """Read-only tool listing SaucerSwap liquidity pools and reserves."""

    def __init__(self, context: Context | None = None):
        self.method = SAUCERSWAP_GET_POOLS_TOOL
        self.name = "SaucerSwap Get Pools"
        self.description = (
            "Query SaucerSwap liquidity pools and their reserves. Optionally filter by a "
            "token pair and limit the number of results. Read-only."
        )
        self.parameters = PoolsParameters

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> PoolsParameters:
        if isinstance(params, PoolsParameters):
            return params
        return PoolsParameters.model_validate(params)

    async def core_action(
        self, normalized_params: PoolsParameters, context: Context, client: Client
    ) -> ToolResponse:
        config = resolve_saucerswap_config(context)
        api = get_api_client(context, config)
        args = normalized_params

        version = args.version or config.default_pool_version
        pools = await api.get_pools(version)

        filtered = pools
        if args.token_a and args.token_b:
            token_a_id = await api.resolve_token_id(normalize_token_alias(args.token_a, config))
            token_b_id = await api.resolve_token_id(normalize_token_alias(args.token_b, config))
            filtered = [
                pool
                for pool in pools
                if {pool.get("tokenA", {}).get("id"), pool.get("tokenB", {}).get("id")}
                == {token_a_id, token_b_id}
            ]

        if args.limit:
            filtered = filtered[: args.limit]

        return ToolResponse(
            human_message=json.dumps(
                {"version": version, "pool_count": len(filtered)}, default=str
            ),
            extra={"success": True, "version": version, "pools": filtered},
        )

    async def should_secondary_action(self, core_result: Any, context: Context) -> bool:
        return False


pools_tool = PoolsTool
