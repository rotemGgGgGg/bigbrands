"""Minimal Solana JSON-RPC client plus buy extraction from parsed transactions.

Deliberately provider-agnostic: works against Helius, QuickNode, Alchemy or the
public endpoint. The only thing that changes is RPC_URL and the rate limit.
"""
import threading
import time
from typing import Optional

import requests

import config

LAMPORTS_PER_SOL = 1_000_000_000
WSOL = "So11111111111111111111111111111111111111112"


class RateLimiter:
    """Simple token bucket so we stay inside a free tier's rps allowance."""

    def __init__(self, rps: float):
        self.min_interval = 1.0 / rps if rps > 0 else 0.0
        self._lock = threading.Lock()
        self._next_at = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._next_at - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._next_at = now + self.min_interval


class RpcError(Exception):
    pass


class SolanaRpc:
    def __init__(self, url: str = None, rps: float = None):
        self.url = url or config.RPC_URL
        self.limiter = RateLimiter(rps if rps is not None else config.RPC_RPS)
        self.session = requests.Session()
        self._id = 0

    def call(self, method: str, params: list, retries: int = 3):
        payload_id = self._id = self._id + 1
        body = {"jsonrpc": "2.0", "id": payload_id, "method": method, "params": params}
        backoff = 1.0
        for attempt in range(retries + 1):
            self.limiter.acquire()
            try:
                resp = self.session.post(self.url, json=body, timeout=config.RPC_TIMEOUT)
            except requests.RequestException as exc:
                if attempt == retries:
                    raise RpcError(f"{method}: {exc}") from exc
                time.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code == 429:
                # Rate limited: back off and try again.
                if attempt == retries:
                    raise RpcError(f"{method}: rate limited")
                time.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code >= 500:
                if attempt == retries:
                    raise RpcError(f"{method}: HTTP {resp.status_code}")
                time.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code != 200:
                raise RpcError(f"{method}: HTTP {resp.status_code} {resp.text[:200]}")
            data = resp.json()
            if "error" in data:
                raise RpcError(f"{method}: {data['error']}")
            return data.get("result")
        raise RpcError(f"{method}: exhausted retries")

    def get_signatures(self, address: str, until: Optional[str] = None, limit: int = 25) -> list:
        """Newest-first signature list for an address, stopping at `until`."""
        params = [address, {"limit": limit}]
        if until:
            params[1]["until"] = until
        return self.call("getSignaturesForAddress", params) or []

    def get_transaction(self, signature: str) -> Optional[dict]:
        return self.call(
            "getTransaction",
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 1,
                    "commitment": "confirmed",
                },
            ],
        )


def extract_buys(tx: dict, owner: str) -> list:
    """Return [{mint, amount, sol_spent}] for tokens `owner` net-acquired in `tx`.

    A "buy" is: the owner's balance of some non-ignored mint went up, while the
    owner net-spent SOL (native or wrapped) in the same transaction. That covers
    Jupiter/Raydium/pump.fun swaps without needing per-DEX parsing, and it
    naturally excludes airdrops and plain transfers in (no SOL spent).
    """
    if not tx or tx.get("meta", {}).get("err") is not None:
        return []

    meta = tx["meta"]
    message = tx["transaction"]["message"]
    account_keys = [
        k["pubkey"] if isinstance(k, dict) else k for k in message.get("accountKeys", [])
    ]

    # Native SOL delta for the owner (includes fees; good enough as a proxy).
    sol_delta = 0.0
    if owner in account_keys:
        idx = account_keys.index(owner)
        pre = meta.get("preBalances", [])
        post = meta.get("postBalances", [])
        if idx < len(pre) and idx < len(post):
            sol_delta = (post[idx] - pre[idx]) / LAMPORTS_PER_SOL

    def token_map(entries):
        out = {}
        for entry in entries or []:
            if entry.get("owner") != owner:
                continue
            amount = entry.get("uiTokenAmount", {}).get("uiAmount")
            out[entry["mint"]] = float(amount or 0.0)
        return out

    pre_tokens = token_map(meta.get("preTokenBalances"))
    post_tokens = token_map(meta.get("postTokenBalances"))

    # Wrapped SOL moves count as spending too.
    wsol_delta = post_tokens.get(WSOL, 0.0) - pre_tokens.get(WSOL, 0.0)
    spent = -(sol_delta + wsol_delta)
    if spent < config.MIN_SOL_BUY:
        return []

    buys = []
    for mint in set(pre_tokens) | set(post_tokens):
        if mint in config.IGNORED_MINTS:
            continue
        delta = post_tokens.get(mint, 0.0) - pre_tokens.get(mint, 0.0)
        if delta > 0:
            buys.append({"mint": mint, "amount": delta, "sol_spent": spent})

    if len(buys) > 1:
        # Split the SOL across mints so a multi-hop route is not double counted.
        for buy in buys:
            buy["sol_spent"] = spent / len(buys)
    return buys
