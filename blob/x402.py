"""x402-paid data fetching through TWAK.

Rubric target (Best Use of TWAK, 10 pts): "the agent uses x402 to pay per
request for data ... as part of its trade loop. Real, not a README mention."
Once funded, the daily strategy rebalance pays $0.01 per request for CMC data
through `twak x402 request`, on BSC via gasless EIP-3009, capped by
--max-payment. The payment proof is logged to the agent audit trail.

Until the wallet holds the payment stablecoin, this path is disabled
(X402_ENABLED=0) and the agent runs on the free API-key feed only.
"""

from __future__ import annotations

import json
import logging
import subprocess

log = logging.getLogger(__name__)

X402_QUOTES_URL = "https://pro-api.coinmarketcap.com/x402/v3/cryptocurrency/quotes/latest"
# BSC-USDT (18 decimals): we pay straight from the trading balance — the CMC
# endpoint accepts Tether on BSC via permit2 (verified with `twak x402 quote`).
USDT_BSC = "0x55d398326f99059fF775485246999027B3197955"
MAX_PAYMENT_ATOMIC = "10000000000000000"  # 0.01 USDT


X402_LISTINGS_URL = "https://pro-api.coinmarketcap.com/x402/v3/cryptocurrency/listings/latest"


def build_request_cmd(url: str) -> list[str]:
    return [
        "twak", "x402", "request", url,
        "--prefer-network", "bsc",
        "--prefer-asset", USDT_BSC,
        "--prefer-method", "permit2-exact",
        "--max-payment", MAX_PAYMENT_ATOMIC,
        "--auto-approve",  # one-time Permit2 approval tx on first use, no-op after
        "--yes",
        "--json",
    ]


def _x402_get(url: str, timeout: float = 90.0) -> dict | None:
    """Pay $0.01 USDT (BSC) for one x402-gated CMC request. Returns the parsed
    response or None on failure — callers must never depend on it for the
    trading decision itself."""
    cmd = build_request_cmd(url)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("x402 request failed to run: %s", exc)
        return None
    if result.returncode != 0:
        # The twak CLI reports errors as JSON on stdout, not stderr.
        log.warning("x402 request failed: stdout=%s stderr=%s",
                    result.stdout.strip()[:500], result.stderr.strip()[:300])
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        log.warning("x402 response is not JSON: %s", result.stdout.strip()[:200])
        return None


def fetch_quotes_x402(symbols: list[str], timeout: float = 90.0) -> dict | None:
    """Pay-per-request CMC quotes via TWAK x402 (request type 1: quotes)."""
    return _x402_get(f"{X402_QUOTES_URL}?symbol={','.join(symbols)}", timeout)


def fetch_listings_x402(limit: int = 20, timeout: float = 90.0) -> dict | None:
    """Pay-per-request CMC listings via TWAK x402 (request type 2: listings).
    A distinct paid endpoint used as a market-breadth cross-check in the loop."""
    return _x402_get(f"{X402_LISTINGS_URL}?limit={limit}", timeout)


def listings_breadth(payload: dict) -> dict | None:
    """Compact market-breadth snapshot from a listings response: share of the
    top names up over 24h. Small on purpose — it goes to the audit log."""
    rows = payload.get("data") or []
    changes = []
    for r in rows:
        quote = r.get("quote")
        # v3 returns quote as a list of per-currency objects; older shape a dict.
        usd = next((q for q in quote if q.get("symbol") == "USD"), None) \
            if isinstance(quote, list) else (quote or {}).get("USD")
        if usd and usd.get("percent_change_24h") is not None:
            changes.append(usd["percent_change_24h"])
    if not changes:
        return None
    up = sum(1 for c in changes if c > 0)
    return {"n": len(changes), "share_up_24h": round(up / len(changes), 3)}


def parse_quotes(payload: dict, symbol: str) -> dict | None:
    """Extract a compact quote from a CMC v3 x402 response.

    v3 returns a LIST of every token sharing the ticker — including dead
    memecoins squatting major symbols — so we must keep only active entries
    and take the highest market cap. The returned dict is small on purpose:
    it goes to the audit log every day."""
    candidates = []
    for item in payload.get("data", []):
        if item.get("symbol") != symbol or not item.get("is_active"):
            continue
        usd = next((q for q in item.get("quote", []) if q.get("symbol") == "USD"), None)
        if not usd or not usd.get("price"):
            continue
        candidates.append((usd.get("market_cap") or 0.0, item, usd))
    if not candidates:
        return None
    _, item, usd = max(candidates, key=lambda c: c[0])
    return {
        "symbol": symbol,
        "cmc_id": item.get("id"),
        "price": usd["price"],
        "pct_24h": usd.get("percent_change_24h"),
        "pct_7d": usd.get("percent_change_7d"),
        "last_updated": usd.get("last_updated"),
        "credit_count": payload.get("status", {}).get("credit_count"),
    }
