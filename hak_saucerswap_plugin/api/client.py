"""Async HTTP client for the SaucerSwap REST API with retries and token caching."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from .endpoints import SAUCER_ENDPOINTS

TOKEN_ID_RE = re.compile(r"^\d+\.\d+\.\d+$")

RETRYABLE_STATUS = {429}


def _is_retryable_status(status: int) -> bool:
    return status in RETRYABLE_STATUS or 500 <= status < 600


class SaucerSwapClient:
    """Thin wrapper over the SaucerSwap REST API.

    Accepts an optional pre-configured ``httpx.AsyncClient`` (``http``) so a
    host application can inject auth headers or custom transports.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://api.saucerswap.finance",
        timeout_seconds: float = 10.0,
        retries: int = 2,
        api_key: str | None = None,
        http: httpx.AsyncClient | None = None,
    ):
        self.retries = retries
        if http is not None:
            self._http = http
        else:
            headers = {"x-api-key": api_key} if api_key else None
            self._http = httpx.AsyncClient(
                base_url=base_url, timeout=timeout_seconds, headers=headers
            )
        self._tokens_cache: list[dict[str, Any]] | None = None
        self._token_index: dict[str, dict[str, Any]] | None = None

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = await self._http.get(path, params=params)
                if _is_retryable_status(response.status_code) and attempt < self.retries:
                    await asyncio.sleep(0.2 * 2**attempt)
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as error:
                last_error = error
                retryable = isinstance(error, httpx.TransportError) or (
                    isinstance(error, httpx.HTTPStatusError)
                    and _is_retryable_status(error.response.status_code)
                )
                if attempt < self.retries and retryable:
                    await asyncio.sleep(0.2 * 2**attempt)
                    continue
                raise
        raise last_error if last_error else RuntimeError("SaucerSwap request failed")

    async def get_tokens(self) -> list[dict[str, Any]]:
        tokens = await self._request(SAUCER_ENDPOINTS["tokens"])
        self._cache_tokens(tokens)
        return tokens

    async def get_token_by_id_or_symbol(self, value: str) -> dict[str, Any] | None:
        if self._token_index is None:
            await self.get_tokens()
        assert self._token_index is not None
        return self._token_index.get(value.lower())

    async def resolve_token_id(self, value: str) -> str:
        if TOKEN_ID_RE.match(value):
            return value
        token = await self.get_token_by_id_or_symbol(value)
        return token["id"] if token else value

    async def get_pools(self, version: str) -> list[dict[str, Any]]:
        endpoint = (
            SAUCER_ENDPOINTS["pools_v1"] if version == "v1" else SAUCER_ENDPOINTS["pools_v2"]
        )
        return await self._request(endpoint)

    async def get_pool_by_tokens(
        self, token_a: str, token_b: str, version: str
    ) -> dict[str, Any] | None:
        pools = await self.get_pools(version)
        for pool in pools:
            a = pool.get("tokenA", {}).get("id")
            b = pool.get("tokenB", {}).get("id")
            if (a == token_a and b == token_b) or (a == token_b and b == token_a):
                return pool
        return None

    async def get_swap_quote(
        self, *, from_token: str, to_token: str, amount: str
    ) -> dict[str, Any]:
        return await self._request(
            SAUCER_ENDPOINTS["swap_quote"],
            params={
                "tokenIn": from_token,
                "tokenOut": to_token,
                "amount": amount,
                "fromToken": from_token,
                "toToken": to_token,
            },
        )

    async def get_farms(self) -> list[dict[str, Any]]:
        return await self._request(SAUCER_ENDPOINTS["farms"])

    async def get_stats(self) -> dict[str, Any]:
        return await self._request(SAUCER_ENDPOINTS["stats"])

    async def aclose(self) -> None:
        await self._http.aclose()

    def _cache_tokens(self, tokens: list[dict[str, Any]]) -> None:
        self._tokens_cache = tokens
        self._token_index = {}
        for token in tokens:
            for key in ("id", "symbol", "name"):
                value = token.get(key)
                if isinstance(value, str):
                    self._token_index[value.lower()] = token


def create_saucerswap_client(
    config: Any, http: httpx.AsyncClient | None = None
) -> SaucerSwapClient:
    return SaucerSwapClient(
        base_url=config.base_url,
        timeout_seconds=config.timeout_seconds,
        retries=config.retries,
        api_key=config.api_key,
        http=http,
    )
