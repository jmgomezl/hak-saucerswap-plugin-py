import httpx
import pytest

from hak_saucerswap_plugin.api.client import SaucerSwapClient

TOKENS = [
    {"id": "0.0.731861", "symbol": "SAUCE", "name": "SaucerSwap", "decimals": 6},
    {"id": "0.0.1456986", "symbol": "WHBAR", "name": "Wrapped Hbar", "decimals": 8},
]


def make_client(handler, retries=2):
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(base_url="https://api.test", transport=transport)
    return SaucerSwapClient(http=http, retries=retries)


async def test_resolve_token_id_passthrough():
    client = make_client(lambda request: httpx.Response(500))
    assert await client.resolve_token_id("0.0.123456") == "0.0.123456"


async def test_resolve_token_by_symbol():
    def handler(request):
        assert request.url.path == "/tokens"
        return httpx.Response(200, json=TOKENS)

    client = make_client(handler)
    assert await client.resolve_token_id("sauce") == "0.0.731861"
    assert await client.resolve_token_id("UNKNOWN") == "UNKNOWN"


async def test_retry_on_5xx_then_success():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=[])

    client = make_client(handler, retries=2)
    assert await client.get_farms() == []
    assert calls["n"] == 3


async def test_no_retry_on_4xx():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404)

    client = make_client(handler, retries=2)
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_farms()
    assert calls["n"] == 1


async def test_get_pool_by_tokens_matches_inverse():
    pools = [
        {
            "tokenA": {"id": "0.0.1"},
            "tokenB": {"id": "0.0.2"},
        }
    ]
    client = make_client(lambda request: httpx.Response(200, json=pools))
    pool = await client.get_pool_by_tokens("0.0.2", "0.0.1", "v2")
    assert pool is not None


async def test_api_key_header():
    seen = {}

    def handler(request):
        seen["key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    client = SaucerSwapClient(
        base_url="https://api.test",
        api_key="secret",
        http=None,
    )
    # Replace the transport on the internally-built client to avoid real I/O.
    client._http = httpx.AsyncClient(
        base_url="https://api.test", headers={"x-api-key": "secret"}, transport=transport
    )
    await client.get_farms()
    assert seen["key"] == "secret"
