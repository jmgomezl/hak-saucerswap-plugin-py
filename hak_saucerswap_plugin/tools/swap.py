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
from ..utils.quote import normalize_swap_quote
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

SAUCERSWAP_SWAP_TOKENS_TOOL = "saucerswap_swap_tokens"


class SwapParameters(BaseModel):
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
    deadline: float | None = Field(
        default=None,
        description="Transaction deadline: minutes from now, or an absolute unix timestamp",
    )


def _post_process(response: RawTransactionResponse) -> str:
    return (
        f"SaucerSwap swap submitted. Status: {response.status}. "
        f"Transaction ID: {response.transaction_id}"
    )


class SwapTool(BaseToolV2):
    """Executes a token swap through the SaucerSwap router contract."""

    def __init__(self, context: Context | None = None):
        self.method = SAUCERSWAP_SWAP_TOKENS_TOOL
        self.name = "SaucerSwap Swap Tokens"
        self.description = (
            "Execute a token swap on the SaucerSwap DEX via the router contract "
            "(swapExactTokensForTokens). Requires an operator account. Token amounts are "
            "decimal-formatted; slippage protection is applied to the minimum output."
        )
        self.parameters = SwapParameters

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> SwapParameters:
        if isinstance(params, SwapParameters):
            return params
        return SwapParameters.model_validate(params)

    async def core_action(
        self, normalized_params: SwapParameters, context: Context, client: Client
    ) -> Any:
        config = resolve_saucerswap_config(context)
        args = normalized_params

        operator_account_id = get_operator_account_id(client, context)
        if not operator_account_id:
            message = "Hedera client with an operator account is required for swaps."
            return ToolResponse(human_message=message, error=message)

        api = get_api_client(context, config)

        from_token_id = await api.resolve_token_id(normalize_token_alias(args.from_token, config))
        to_token_id = await api.resolve_token_id(normalize_token_alias(args.to_token, config))

        from_token_meta = await api.get_token_by_id_or_symbol(from_token_id)
        to_token_meta = await api.get_token_by_id_or_symbol(to_token_id)
        if not from_token_meta or not to_token_meta:
            message = "Unable to resolve token metadata from SaucerSwap API."
            return ToolResponse(human_message=message, error=message)

        quote = normalize_swap_quote(
            await api.get_swap_quote(
                from_token=from_token_id, to_token=to_token_id, amount=args.amount
            ),
            args.amount,
        )

        amount_in_smallest = parse_units(args.amount, from_token_meta["decimals"])
        expected = quote["expected_output"]
        expected_out_smallest = (
            parse_units(expected, to_token_meta["decimals"]) if "." in expected else expected
        )
        min_out_smallest = apply_slippage_to_amount(expected_out_smallest, args.slippage_tolerance)

        router_contract_id = resolve_router_contract(config)
        deadline = resolve_deadline(args.deadline, config.deadline_minutes)
        to_address = account_id_to_evm_address(operator_account_id)
        path = [
            token_id_to_evm_address(require_token_id(from_token_id)),
            token_id_to_evm_address(require_token_id(to_token_id)),
        ]

        params = (
            ContractFunctionParameters()
            .add_uint256(int(amount_in_smallest))
            .add_uint256(int(min_out_smallest))
            .add_address_array(path)
            .add_address(to_address)
            .add_uint256(deadline)
        )
        transaction = (
            ContractExecuteTransaction()
            .set_contract_id(contract_id_from_string(router_contract_id))
            .set_gas(config.gas_limit)
            .set_function("swapExactTokensForTokens", params)
        )

        return {
            "transaction": transaction,
            "extras": {
                "estimated_output": quote["expected_output"],
                "min_output": min_out_smallest,
                "price_impact": quote["price_impact"],
                "route": quote["route"],
            },
        }

    async def should_secondary_action(self, core_result: Any, context: Context) -> bool:
        return isinstance(core_result, dict) and "transaction" in core_result

    async def secondary_action(
        self, core_result: Any, client: Client, context: Context
    ) -> ToolResponse:
        response = await handle_transaction(
            core_result["transaction"], client, context, _post_process
        )
        response.extra.update(core_result["extras"])
        return response

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        message = f"Failed to execute SaucerSwap swap: {error}"
        return ToolResponse(human_message=message, error=message)


swap_tool = SwapTool
