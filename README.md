# hak-saucerswap-plugin (Python)

A [Hedera Agent Kit](https://github.com/hashgraph/hedera-agent-kit-py) plugin that integrates the [SaucerSwap](https://saucerswap.finance) DEX, letting AI agents quote swaps, execute trades, manage liquidity, and explore farming opportunities on Hedera.

Python port of the TypeScript plugin [`hak-saucerswap-plugin`](https://github.com/jmgomezl/hak-saucerswap-plugin).

## Tools

| Method | Description | On-chain |
| --- | --- | --- |
| `saucerswap_get_swap_quote` | Price quote with min output, price impact, and route | No |
| `saucerswap_swap_tokens` | Execute a swap via the router (`swapExactTokensForTokens`) | Yes |
| `saucerswap_get_pools` | List/filter liquidity pools and reserves | No |
| `saucerswap_add_liquidity` | Add liquidity to a pool (`addLiquidity`) | Yes |
| `saucerswap_remove_liquidity` | Burn LP tokens for the underlying pair (`removeLiquidity`) | Yes |
| `saucerswap_get_farms` | List active yield farms | No |

## Installation

```bash
pip install hak-saucerswap-plugin
```

## Usage

```python
from hedera_agent_kit.shared.configuration import AgentMode, Configuration, Context
from hak_saucerswap_plugin import saucerswap_plugin

context = Context(account_id="0.0.xxxx", mode=AgentMode.AUTONOMOUS)
# Attach plugin configuration to the context (optional; env vars also work):
context.saucerswap = {"network": "mainnet"}

configuration = Configuration(plugins=[saucerswap_plugin], context=context)
```

## Configuration

Settings resolve with this precedence: context config → environment variables → network defaults → built-in defaults.

| Context key | Env var | Description | Default |
| --- | --- | --- | --- |
| `base_url` | `SAUCERSWAP_BASE_URL` | SaucerSwap REST API base URL | `https://api.saucerswap.finance` |
| `api_key` | `SAUCERSWAP_API_KEY` | API key sent as `x-api-key` (request at support@saucerswap.finance) | — |
| `network` | `SAUCERSWAP_NETWORK` | `mainnet` or `testnet`; fills router/WHBAR/alias defaults | — |
| `timeout_seconds` | `SAUCERSWAP_TIMEOUT_SECONDS` | HTTP timeout in seconds | `10` |
| `retries` | `SAUCERSWAP_RETRIES` | Retries for 429/5xx/transport errors | `2` |
| `router_contract_id` | `SAUCERSWAP_ROUTER_CONTRACT_ID` | V1 router contract ID | from network |
| `router_v2_contract_id` | `SAUCERSWAP_ROUTER_V2_CONTRACT_ID` | V2 router contract ID | from network |
| `wrapped_hbar_token_id` | `SAUCERSWAP_WRAPPED_HBAR_TOKEN_ID` | WHBAR token ID (used for the `HBAR` alias) | from network |
| `token_aliases` | `SAUCERSWAP_TOKEN_ALIASES` | Symbol → token ID map (env var takes JSON) | from network |
| `default_pool_version` | `SAUCERSWAP_DEFAULT_POOL_VERSION` | `v1` or `v2` | `v2` |
| `gas_limit` | `SAUCERSWAP_GAS_LIMIT` | Gas limit for router calls | `2000000` |
| `deadline_minutes` | `SAUCERSWAP_DEADLINE_MINUTES` | Default transaction deadline | `20` |

Network defaults (contract addresses from the [official SaucerSwap deployments](https://docs.saucerswap.finance/developerx/contract-deployments)) are exported as `SAUCERSWAP_MAINNET` and `SAUCERSWAP_TESTNET`.

A pre-configured `httpx.AsyncClient` can also be injected by attaching it to the context as `context.saucerswap_client` (e.g. to share auth headers or transports).

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

## License

MIT
