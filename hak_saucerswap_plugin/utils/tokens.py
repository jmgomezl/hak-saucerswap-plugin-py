from __future__ import annotations

import re

from hiero_sdk_python import AccountId, TokenId
from hiero_sdk_python.contract.contract_id import ContractId

from ..config import SaucerSwapConfig

TOKEN_ID_RE = re.compile(r"^\d+\.\d+\.\d+$")


def normalize_token_alias(token: str, config: SaucerSwapConfig) -> str:
    token_lower = token.lower()
    for alias, value in config.token_aliases.items():
        if alias.lower() == token_lower:
            return value
    if token_lower == "hbar" and config.wrapped_hbar_token_id:
        return config.wrapped_hbar_token_id
    return token


def require_token_id(token: str) -> str:
    if not TOKEN_ID_RE.match(token):
        raise ValueError(f"Token ID required for on-chain actions: {token}")
    return token


def _entity_to_evm_address(shard: int, realm: int, num: int) -> str:
    return f"{shard:08x}{realm:016x}{num:016x}"


def token_id_to_evm_address(token_id: str) -> str:
    t = TokenId.from_string(token_id)
    return _entity_to_evm_address(t.shard, t.realm, t.num)


def account_id_to_evm_address(account_id: str) -> str:
    a = AccountId.from_string(account_id)
    address = getattr(a, "to_evm_address", None)
    if callable(address):
        return address()
    return _entity_to_evm_address(a.shard, a.realm, a.num)


def contract_id_from_string(contract_id: str) -> ContractId:
    return ContractId.from_string(contract_id)
