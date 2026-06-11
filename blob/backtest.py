"""Backtest harness: replays the EXACT production decision path
(strategy.target_allocation -> risk.apply -> plan_orders -> PaperExecutor)
on historical hourly data.

Primary metric: COMPETITION WINDOWS — independent 7-day simulations starting
at every midnight, each with fresh capital and a fresh drawdown peak, matching
the real contest format (June 22-28). A continuous simulation is also reported
as a sanity check, but its drawdown ladder compounds across the whole period,
which is not how the one-week competition behaves.

Keyless data sources (runs without any credentials):
- Binance public klines API (hourly closes; symbols missing on Binance spot
  are skipped with a warning)
- alternative.me Fear & Greed index (daily history)

Costs are the flat cost_per_side from Config; the organizers' simulated cost
model is still unconfirmed (docs/redteam.md R4).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import httpx

from . import risk
from .config import Config
from .datafeed import Quote
from .execution import PaperExecutor, plan_orders
from .portfolio import Portfolio
from .strategy import Decision, target_allocation
from .universe import ALLOWLIST, BASE, REGIME_ANCHOR

log = logging.getLogger(__name__)

HOUR_MS = 3_600_000
WARMUP_HOURS = 168   # need 7d of history before the first decision
WINDOW_HOURS = 168   # competition window length
DQ_DRAWDOWN = 0.30   # official disqualification gate (example value in rules)


# --------------------------------------------------------------------------
# Data fetching
# --------------------------------------------------------------------------

def fetch_klines(client: httpx.Client, pair: str, start_ms: int, end_ms: int) -> dict[int, float]:
    """Hourly closes keyed by open time (ms)."""
    out: dict[int, float] = {}
    cursor = start_ms
    while cursor < end_ms:
        resp = client.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": pair, "interval": "1h", "startTime": cursor,
                    "endTime": end_ms, "limit": 1000},
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        for r in rows:
            out[int(r[0])] = float(r[4])
        cursor = int(rows[-1][0]) + HOUR_MS
        if len(rows) < 1000:
            break
        time.sleep(0.1)
    return out


def fetch_fear_greed_daily(client: httpx.Client) -> dict[str, int]:
    """ISO date -> index value, from alternative.me (free, no key)."""
    resp = client.get("https://api.alternative.me/fng/", params={"limit": 0, "format": "json"})
    resp.raise_for_status()
    out: dict[str, int] = {}
    for row in resp.json()["data"]:
        date = datetime.fromtimestamp(int(row["timestamp"]), tz=timezone.utc).date().isoformat()
        out[date] = int(row["value"])
    return out


def fetch_data(days: int) -> tuple[dict[str, dict[int, float]], dict[str, int], list[int]]:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000) // HOUR_MS * HOUR_MS
    start_ms = now_ms - (days * 24 + WARMUP_HOURS) * HOUR_MS

    closes: dict[str, dict[int, float]] = {}
    with httpx.Client(timeout=30) as client:
        for symbol in [REGIME_ANCHOR] + ALLOWLIST:
            try:
                series = fetch_klines(client, symbol + "USDT", start_ms, now_ms)
            except httpx.HTTPError as exc:
                log.warning("skipping %s: %s", symbol, exc)
                continue
            if len(series) < WARMUP_HOURS + 24:
                log.warning("skipping %s: not enough history (%d candles)", symbol, len(series))
                continue
            closes[symbol] = series
        fear_greed = fetch_fear_greed_daily(client)

    if REGIME_ANCHOR not in closes:
        raise RuntimeError("no anchor data, aborting")
    timeline = sorted(t for t in closes[REGIME_ANCHOR] if t >= start_ms + WARMUP_HOURS * HOUR_MS)
    return closes, fear_greed, timeline


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------

def _build_quotes(closes: dict[str, dict[int, float]], ts: int) -> dict[str, Quote]:
    quotes: dict[str, Quote] = {}
    for symbol, series in closes.items():
        price = series.get(ts)
        ref_24h = series.get(ts - 24 * HOUR_MS)
        ref_7d = series.get(ts - WINDOW_HOURS * HOUR_MS)
        if not price or not ref_24h or not ref_7d:
            continue
        quotes[symbol] = Quote(
            symbol=symbol, price=price,
            pct_1h=0.0,
            pct_24h=(price / ref_24h - 1.0) * 100.0,
            pct_7d=(price / ref_7d - 1.0) * 100.0,
            market_cap=0.0,
        )
    return quotes


def _simulate(
    closes: dict[str, dict[int, float]],
    fear_greed: dict[str, int],
    cfg: Config,
    hours: list[int],
) -> dict:
    """Run the production pipeline over consecutive hourly timestamps with
    fresh capital. Returns final stats for that span."""
    portfolio = Portfolio(holdings={BASE: cfg.paper_start_usdt}, peak_value=cfg.paper_start_usdt)
    executor = PaperExecutor(cfg)
    trades = 0
    max_dd = 0.0
    value = cfg.paper_start_usdt
    for ts in hours:
        prices = {s: series[ts] for s, series in closes.items() if ts in series}
        if not prices:
            continue
        value, drawdown = portfolio.mark(prices)
        max_dd = max(max_dd, drawdown)
        # Mirror production: daily strategy rebalance at 00:00 UTC, hourly
        # risk-only check otherwise (the drawdown ladder must act intraday).
        if datetime.fromtimestamp(ts / 1000, tz=timezone.utc).hour == 0:
            quotes = _build_quotes(closes, ts)
            date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
            held = {s for s, q in portfolio.holdings.items() if s != BASE and q > 1e-12}
            decision = target_allocation(quotes, fear_greed.get(date, 50), cfg, held)
        else:
            weights = portfolio.weights(prices)
            decision = Decision(
                exposure=sum(w for s, w in weights.items() if s != BASE),
                weights=weights,
                reasons=[],
            )
        decision = risk.apply(decision, drawdown, cfg)
        for order in plan_orders(portfolio, prices, decision.weights, cfg):
            if executor.execute(order, prices, portfolio):
                trades += 1
    return {
        "return": value / cfg.paper_start_usdt - 1.0,
        "max_drawdown": max_dd,
        "trades": trades,
    }


def _quantile(sorted_values: list[float], p: float) -> float:
    return sorted_values[min(int(p * len(sorted_values)), len(sorted_values) - 1)]


def run_backtest(cfg: Config, days: int = 90, data=None) -> dict:
    closes, fear_greed, timeline = data if data is not None else fetch_data(days)

    # Competition windows: fresh 7-day runs starting at every midnight.
    midnights = [
        i for i, ts in enumerate(timeline)
        if datetime.fromtimestamp(ts / 1000, tz=timezone.utc).hour == 0
    ]
    windows = []
    for i in midnights:
        if i + WINDOW_HOURS >= len(timeline):
            break
        windows.append(_simulate(closes, fear_greed, cfg, timeline[i: i + WINDOW_HOURS]))

    returns = sorted(w["return"] for w in windows)
    overall = _simulate(closes, fear_greed, cfg, timeline)

    eth = closes.get("ETH", {})
    bench = (eth[timeline[-1]] / eth[timeline[0]] - 1.0) if timeline[0] in eth and timeline[-1] in eth else None

    return {
        "days": days,
        "symbols_used": sorted(closes),
        "competition_windows_7d": {
            "n": len(windows),
            "min": round(returns[0], 4),
            "p25": round(_quantile(returns, 0.25), 4),
            "median": round(_quantile(returns, 0.5), 4),
            "p75": round(_quantile(returns, 0.75), 4),
            "p90": round(_quantile(returns, 0.90), 4),
            "max": round(returns[-1], 4),
            "share_positive": round(sum(1 for r in returns if r > 0) / len(returns), 3),
            "dq_rate": round(sum(1 for w in windows if w["max_drawdown"] >= DQ_DRAWDOWN) / len(windows), 3),
            "worst_window_drawdown": round(max(w["max_drawdown"] for w in windows), 4),
            "avg_trades_per_window": round(sum(w["trades"] for w in windows) / len(windows), 1),
        },
        "continuous": {
            "total_return": round(overall["return"], 4),
            "max_drawdown": round(overall["max_drawdown"], 4),
            "trades": overall["trades"],
            "note": "drawdown ladder compounds over the full period; competition windows above are the relevant metric",
        },
        "eth_buy_hold_return": round(bench, 4) if bench is not None else None,
    }


def run_comparison(cfg: Config, days: int) -> dict:
    """Baseline vs fast-lane on the same fetched data."""
    from dataclasses import replace

    data = fetch_data(days)
    out = {}
    for label, c in (("baseline", replace(cfg, fast_lane=False)),
                     ("fast_lane", replace(cfg, fast_lane=True))):
        result = run_backtest(c, days, data=data)
        result.pop("symbols_used")
        out[label] = result
    return out
