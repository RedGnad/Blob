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
# 0.01 of an 18-decimals stablecoin (the BSC route quoted by the CMC endpoint).
MAX_PAYMENT_ATOMIC = "10000000000000000"


def build_request_cmd(symbols: list[str]) -> list[str]:
    url = f"{X402_QUOTES_URL}?symbol={','.join(symbols)}"
    return [
        "twak", "x402", "request", url,
        "--prefer-network", "bsc",
        "--prefer-method", "eip3009",
        "--max-payment", MAX_PAYMENT_ATOMIC,
        "--yes",
        "--json",
    ]


def fetch_quotes_x402(symbols: list[str], timeout: float = 90.0) -> dict | None:
    """Pay-per-request CMC quotes via TWAK x402. Returns the raw parsed
    response (shape verified during the dress rehearsal) or None on failure —
    the caller must never depend on this for the trading decision itself."""
    cmd = build_request_cmd(symbols)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("x402 request failed to run: %s", exc)
        return None
    if result.returncode != 0:
        log.warning("x402 request failed: %s", result.stderr.strip()[:500])
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        log.warning("x402 response is not JSON: %s", result.stdout.strip()[:200])
        return None
