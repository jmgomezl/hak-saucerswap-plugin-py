from __future__ import annotations

from typing import Any

from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import RawTransactionResponse, ToolResponse
from hedera_agent_kit.shared.strategies.tx_mode_strategy import handle_transaction
from hedera_agent_kit.shared.tool_v2 import BaseToolV2
from hiero_sdk_python import Client
from hiero_sdk_python.contract.contract_execute_transaction import ContractExecuteTransaction
from hiero_sdk_python.contract.contract_function_parameters import ContractFunctionParameters
from pydantic import BaseModel, Field

from ..config import resolve_saucerswap_config
from ..utils.amm import apply_slippage_to_amount
from ..utils.tokens import (
    account_id_to_evm_address,
    contract_id_from_string,
    normalize_token_alias,
    require_token_id,
    token_id_to_evm_address,
)
from ..utils.units import parse_units
from .common import (
    get_api_client,
    get_operator_account_id,
    resolve_deadline,
    resolve_router_contract,
)

SAUCERSWAP_ADD_LIQUIDITY_TOOL = "saucerswap_add_liquidity"
SAUCERSWAP_REMOVE_LIQUIDITY_TOOL = "saucerswap_remove_liquidity"


class AddLiquidityParameters(BaseModel):
    token_a: str = Field(description="First token ID or symbol")
    token_b: str = Field(description="Second token ID or symbol")
    amount_a: str = Field(description="Amount of token_a to add (decimal format)")
    amount_b: str = Field(description="Amount of token_b to add (decimal format)")
    slippage_tolerance: float = Field(
        default=0.5, description="Maximum slippage tolerance percentage (default 0.5)"
    )


class RemoveLiquidityParameters(BaseModel):
    token_a: str = Field(description="First token ID or symbol")
    token_b: str = Field(description="Second token ID or symbol")
    lp_token_amount: str = Field(description="Amount of LP tokens to burn (decimal format)")
    min_amount_a: str = Field(description="Minimum amount of token_a to receive")
    min_amount_b: str = Field(description="Minimum amount of token_b to receive")


def _add_post_process(response: RawTransactionResponse) -> str:
    return (
        f"SaucerSwap add liquidity submitted. Status: {response.status}. "
        f"Transaction ID: {response.transaction_id}"
    )


def _remove_post_process(response: RawTransactionResponse) -> str:
    return (
        f"SaucerSwap remove liquidity submitted. Status: {response.status}. "
        f"Transaction ID: {response.transaction_id}"
    )


class AddLiquidityTool(BaseToolV2):
    """Adds liquidity to a SaucerSwap pool via the router contract."""

    def __init__(self, context: Context | None = None):
        self.method = SAUCERSWAP_ADD_LIQUIDITY_TOOL
        self.name = "SaucerSwap Add Liquidity"
        self.description = (
            "Add liquidity to a SaucerSwap pool (router addLiquidity). Requires an operator "
            "account. Amounts are decimal-formatted; slippage protection sets the minimums."
        )
        self.parameters = AddLiquidityParameters

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> AddLiquidityParameters:
        if isinstance(params, AddLiquidityParameters):
            return params
        return AddLiquidityParameters.model_validate(params)

    async def core_action(
        self, normalized_params: AddLiquidityParameters, context: Context, client: Client
    ) -> Any:
        config = resolve_saucerswap_config(context)
        args = normalized_params

        operator_account_id = get_operator_account_id(client, context)
        if not operator_account_id:
            message = "Hedera client with an operator account is required for liquidity actions."
            return ToolResponse(human_message=message, error=message)

        api = get_api_client(context, config)

        token_a_id = await api.resolve_token_id(normalize_token_alias(args.token_a, config))
        token_b_id = await api.resolve_token_id(normalize_token_alias(args.token_b, config))

        token_a = await api.get_token_by_id_or_symbol(token_a_id)
        token_b = await api.get_token_by_id_or_symbol(token_b_id)
        if not token_a or not token_b:
            message = "Unable to resolve token metadata from SaucerSwap API."
            return ToolResponse(human_message=message, error=message)

        amount_a_desired = parse_units(args.amount_a, token_a["decimals"])
        amount_b_desired = parse_units(args.amount_b, token_b["decimals"])
        amount_a_min = apply_slippage_to_amount(amount_a_desired, args.slippage_tolerance)
        amount_b_min = apply_slippage_to_amount(amount_b_desired, args.slippage_tolerance)

        router_contract_id = resolve_router_contract(config)
        deadline = resolve_deadline(None, config.deadline_minutes)
        to_address = account_id_to_evm_address(operator_account_id)

        params = (
            ContractFunctionParameters()
            .add_address(token_id_to_evm_address(require_token_id(token_a_id)))
            .add_address(token_id_to_evm_address(require_token_id(token_b_id)))
            .add_uint256(int(amount_a_desired))
            .add_uint256(int(amount_b_desired))
            .add_uint256(int(amount_a_min))
            .add_uint256(int(amount_b_min))
            .add_address(to_address)
            .add_uint256(deadline)
        )
        transaction = (
            ContractExecuteTransaction()
            .set_contract_id(contract_id_from_string(router_contract_id))
            .set_gas(config.gas_limit)
            .set_function("addLiquidity", params)
        )

        return {
            "transaction": transaction,
            "extras": {
                "amount_a_desired": amount_a_desired,
                "amount_b_desired": amount_b_desired,
                "amount_a_min": amount_a_min,
                "amount_b_min": amount_b_min,
            },
        }

    async def should_secondary_action(self, core_result: Any, context: Context) -> bool:
        return isinstance(core_result, dict) and "transaction" in core_result

    async def secondary_action(
        self, core_result: Any, client: Client, context: Context
    ) -> ToolResponse:
        response = await handle_transaction(
            core_result["transaction"], client, context, _add_post_process
        )
        response.extra.update(core_result["extras"])
        return response

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        message = f"Failed to add liquidity on SaucerSwap: {error}"
        return ToolResponse(human_message=message, error=message)


class RemoveLiquidityTool(BaseToolV2):
    """Removes liquidity from a SaucerSwap pool via the router contract."""

    def __init__(self, context: Context | None = None):
        self.method = SAUCERSWAP_REMOVE_LIQUIDITY_TOOL
        self.name = "SaucerSwap Remove Liquidity"
        self.description = (
            "Remove liquidity from a SaucerSwap pool (router removeLiquidity), burning LP "
            "tokens for the underlying pair. Requires an operator account."
        )
        self.parameters = RemoveLiquidityParameters

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> RemoveLiquidityParameters:
        if isinstance(params, RemoveLiquidityParameters):
            return params
        return RemoveLiquidityParameters.model_validate(params)

    async def core_action(
        self, normalized_params: RemoveLiquidityParameters, context: Context, client: Client
    ) -> Any:
        config = resolve_saucerswap_config(context)
        args = normalized_params

        operator_account_id = get_operator_account_id(client, context)
        if not operator_account_id:
            message = "Hedera client with an operator account is required for liquidity actions."
            return ToolResponse(human_message=message, error=message)

        api = get_api_client(context, config)

        token_a_id = await api.resolve_token_id(normalize_token_alias(args.token_a, config))
        token_b_id = await api.resolve_token_id(normalize_token_alias(args.token_b, config))

        pool = await api.get_pool_by_tokens(token_a_id, token_b_id, config.default_pool_version)
        if not pool:
            message = "Unable to locate pool for the provided token pair."
            return ToolResponse(human_message=message, error=message)

        token_a = await api.get_token_by_id_or_symbol(token_a_id)
        token_b = await api.get_token_by_id_or_symbol(token_b_id)
        if not token_a or not token_b:
            message = "Unable to resolve token metadata from SaucerSwap API."
            return ToolResponse(human_message=message, error=message)

        lp_amount = parse_units(args.lp_token_amount, pool["lpToken"]["decimals"])
        min_amount_a = parse_units(args.min_amount_a, token_a["decimals"])
        min_amount_b = parse_units(args.min_amount_b, token_b["decimals"])

        router_contract_id = resolve_router_contract(config)
        deadline = resolve_deadline(None, config.deadline_minutes)
        to_address = account_id_to_evm_address(operator_account_id)

        params = (
            ContractFunctionParameters()
            .add_address(token_id_to_evm_address(require_token_id(token_a_id)))
            .add_address(token_id_to_evm_address(require_token_id(token_b_id)))
            .add_uint256(int(lp_amount))
            .add_uint256(int(min_amount_a))
            .add_uint256(int(min_amount_b))
            .add_address(to_address)
            .add_uint256(deadline)
        )
        transaction = (
            ContractExecuteTransaction()
            .set_contract_id(contract_id_from_string(router_contract_id))
            .set_gas(config.gas_limit)
            .set_function("removeLiquidity", params)
        )

        return {
            "transaction": transaction,
            "extras": {
                "lp_amount": lp_amount,
                "min_amount_a": min_amount_a,
                "min_amount_b": min_amount_b,
            },
        }

    async def should_secondary_action(self, core_result: Any, context: Context) -> bool:
        return isinstance(core_result, dict) and "transaction" in core_result

    async def secondary_action(
        self, core_result: Any, client: Client, context: Context
    ) -> ToolResponse:
        response = await handle_transaction(
            core_result["transaction"], client, context, _remove_post_process
        )
        response.extra.update(core_result["extras"])
        return response

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        message = f"Failed to remove liquidity on SaucerSwap: {error}"
        return ToolResponse(human_message=message, error=message)
