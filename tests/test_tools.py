from types import SimpleNamespace

from hedera_agent_kit.shared.models import ToolResponse

from hak_saucerswap_plugin import saucerswap_plugin
from hak_saucerswap_plugin.tools import PoolsTool, QuoteTool, SwapTool

SAUCE = {"id": "0.0.731861", "symbol": "SAUCE", "name": "SaucerSwap", "decimals": 6}
WHBAR = {"id": "0.0.1456986", "symbol": "WHBAR", "name": "Wrapped Hbar", "decimals": 8}


class FakeApi:
    def __init__(self, quote=None, pools=None):
        self._tokens = {t["id"]: t for t in (SAUCE, WHBAR)}
        self._tokens.update({t["symbol"].lower(): t for t in (SAUCE, WHBAR)})
        self._quote = quote or {}
        self._pools = pools or []

    async def resolve_token_id(self, value):
        token = self._tokens.get(value) or self._tokens.get(value.lower())
        return token["id"] if token else value

    async def get_token_by_id_or_symbol(self, value):
        return self._tokens.get(value) or self._tokens.get(value.lower())

    async def get_swap_quote(self, *, from_token, to_token, amount):
        return self._quote

    async def get_pools(self, version):
        return self._pools

    async def get_pool_by_tokens(self, token_a, token_b, version):
        for pool in self._pools:
            ids = {pool["tokenA"]["id"], pool["tokenB"]["id"]}
            if ids == {token_a, token_b}:
                return pool
        return None


def make_context(api, network="mainnet"):
    return SimpleNamespace(
        saucerswap={"network": network},
        saucerswap_client=api,
        account_id=None,
        hooks=[],
        mode=None,
    )


def test_plugin_exposes_six_tools():
    context = SimpleNamespace(hooks=[], mode=None, account_id=None)
    tools = saucerswap_plugin.tools(context)
    assert len(tools) == 6
    methods = {tool.method for tool in tools}
    assert methods == {
        "saucerswap_get_swap_quote",
        "saucerswap_swap_tokens",
        "saucerswap_get_pools",
        "saucerswap_add_liquidity",
        "saucerswap_remove_liquidity",
        "saucerswap_get_farms",
    }


async def test_quote_tool_returns_quote():
    api = FakeApi(quote={"amountIn": "1000000", "amountOut": "5000000", "priceImpact": 0.1})
    context = make_context(api)
    tool = QuoteTool(context)
    response = await tool.execute(client=None, context=context, params={
        "from_token": "SAUCE",
        "to_token": "WHBAR",
        "amount": "1",
    })
    assert isinstance(response, ToolResponse)
    assert response.error is None
    assert response.extra["success"] is True
    assert response.extra["quote"]["expected_output"] == "5000000"
    assert response.extra["min_output"] == "4975000"  # 0.5% default slippage


async def test_quote_tool_error_on_missing_output():
    api = FakeApi(quote={})
    context = make_context(api)
    tool = QuoteTool(context)
    response = await tool.execute(client=None, context=context, params={
        "from_token": "SAUCE",
        "to_token": "WHBAR",
        "amount": "1",
    })
    assert response.error is not None


async def test_pools_tool_filters_by_pair():
    pools = [
        {"tokenA": SAUCE, "tokenB": WHBAR, "id": 1},
        {"tokenA": {"id": "0.0.9"}, "tokenB": {"id": "0.0.8"}, "id": 2},
    ]
    api = FakeApi(pools=pools)
    context = make_context(api)
    tool = PoolsTool(context)
    response = await tool.execute(client=None, context=context, params={
        "token_a": "SAUCE",
        "token_b": "WHBAR",
    })
    assert response.extra["success"] is True
    assert [p["id"] for p in response.extra["pools"]] == [1]


async def test_swap_tool_builds_transaction():
    api = FakeApi(quote={"amountIn": "1000000", "amountOut": "5.0"})
    context = make_context(api)
    tool = SwapTool(context)
    client = SimpleNamespace(operator_account_id="0.0.1234")

    payload = await tool.core_action(
        await tool.normalize_params(
            {"from_token": "SAUCE", "to_token": "WHBAR", "amount": "1"}, context, client
        ),
        context,
        client,
    )
    assert isinstance(payload, dict)
    assert "transaction" in payload
    # 5.0 WHBAR with 8 decimals -> 500000000 base units, minus 0.5% slippage
    assert payload["extras"]["min_output"] == "497500000"
    assert await tool.should_secondary_action(payload, context) is True


async def test_swap_tool_requires_operator():
    api = FakeApi(quote={"amountOut": "5.0"})
    context = make_context(api)
    tool = SwapTool(context)
    client = SimpleNamespace(operator_account_id=None)

    result = await tool.core_action(
        await tool.normalize_params(
            {"from_token": "SAUCE", "to_token": "WHBAR", "amount": "1"}, context, client
        ),
        context,
        client,
    )
    assert isinstance(result, ToolResponse)
    assert result.error is not None
    assert await tool.should_secondary_action(result, context) is False
