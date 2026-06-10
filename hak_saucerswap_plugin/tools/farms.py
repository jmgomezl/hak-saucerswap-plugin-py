from __future__ import annotations

import json
from typing import Any

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hiero_sdk_python import Client
from pydantic import BaseModel, Field

from ..config import resolve_saucerswap_config
from .common import get_api_client

SAUCERSWAP_GET_FARMS_TOOL = "saucerswap_get_farms"


class FarmsParameters(BaseModel):
    pool_id: int | None = Field(
        default=None, gt=0, description="Optional pool ID to filter farms"
    )


class FarmsTool(BaseToolV2):
    """Read-only tool listing active SaucerSwap yield farms."""

    def __init__(self, context: Context | None = None):
        self.method = SAUCERSWAP_GET_FARMS_TOOL
        self.name = "SaucerSwap Get Farms"
        self.description = (
            "Get active yield farming opportunities on SaucerSwap, optionally filtered "
            "by pool ID. Read-only."
        )
        self.parameters = FarmsParameters

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> FarmsParameters:
        if isinstance(params, FarmsParameters):
            return params
        return FarmsParameters.model_validate(params)

    async def core_action(
        self, normalized_params: FarmsParameters, context: Context, client: Client
    ) -> ToolResponse:
        config = resolve_saucerswap_config(context)
        api = get_api_client(context, config)

        farms = await api.get_farms()
        if normalized_params.pool_id:
            farms = [farm for farm in farms if farm.get("poolId") == normalized_params.pool_id]

        return ToolResponse(
            human_message=json.dumps({"farm_count": len(farms)}, default=str),
            extra={"success": True, "farms": farms},
        )

    async def should_secondary_action(self, core_result: Any, context: Context) -> bool:
        return False


farms_tool = FarmsTool
