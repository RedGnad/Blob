"""Round-trip execution cost measurement at our actual trade sizes.

Uses `twak swap --quote-only` (free, read-only): quote USDT -> token, feed the
quoted token amount into the reverse quote, and compare USDT in vs USDT out.
This is the real cost floor a rotation must clear (docs/redteam.md R5) and the
basis for pruning illiquid tokens from the allowlist (R7)."""

from __future__ import annotations

import json
import logging
import subprocess
import time

from .universe import ALLOWLIST, BASE, twak_token

log = logging.getLogger(__name__)


def parse_amount(value: str) -> float:
    """'1.987585 USDT' -> 1.987585"""
    return float(value.split()[0])


def quote(amount_or_from: str, from_or_to: str, to: str | None = None,
          usd: float | None = None, timeout: float = 60.0) -> dict | None:
    cmd = ["twak", "swap", amount_or_from, from_or_to]
    if to:
        cmd.append(to)
    if usd is not None:
        cmd += ["--usd", f"{usd:.2f}"]
    cmd += ["--chain", "bsc", "--quote-only", "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return None
        # The CLI may print a human line before the JSON object.
        stdout = result.stdout[result.stdout.index("{"):]
        return json.loads(stdout)
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def round_trip_cost(symbol: str, usd: float) -> float | None:
    """Round-trip cost fraction for USDT -> symbol -> USDT, or None if no route."""
    token = twak_token(symbol)
    leg1 = quote(BASE, token, usd=usd)
    if not leg1:
        return None
    usdt_in = parse_amount(leg1["input"])
    token_out = parse_amount(leg1["output"])
    leg2 = quote(f"{token_out:.10f}", token, BASE)
    if not leg2:
        return None
    usdt_back = parse_amount(leg2["output"])
    if usdt_in <= 0:
        return None
    return 1.0 - usdt_back / usdt_in


def measure_all(usd: float = 5.0) -> dict:
    results: dict[str, float | None] = {}
    for symbol in ALLOWLIST:
        results[symbol] = round_trip_cost(symbol, usd)
        cost = results[symbol]
        log.info("%s: %s", symbol, f"{cost:.2%}" if cost is not None else "NO ROUTE")
        time.sleep(0.3)
    measurable = {s: c for s, c in results.items() if c is not None}
    ranked = sorted(measurable.items(), key=lambda kv: kv[1])
    return {
        "trade_size_usd": usd,
        "costs_pct": {s: round(c * 100, 2) for s, c in ranked},
        "median_pct": round(sorted(measurable.values())[len(measurable) // 2] * 100, 2)
        if measurable else None,
        "no_route": [s for s, c in results.items() if c is None],
    }
