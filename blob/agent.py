"""One agent cycle: data -> strategy -> risk -> orders -> execution -> state.
Every run appends a JSON line to logs/agent.jsonl (audit trail for the judges
and for the demo)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from . import risk
from .config import PROJECT_ROOT, Config
from .datafeed import CmcClient
from .execution import (
    PaperExecutor,
    TwakCliExecutor,
    micro_qualification_order,
    plan_orders,
    sync_live_holdings,
)
from .portfolio import Portfolio
from .strategy import Decision, target_allocation
from .x402 import fetch_quotes_x402
from .universe import ALLOWLIST, BASE, REGIME_ANCHOR

log = logging.getLogger(__name__)

STATE_DIR = PROJECT_ROOT / "state"
LOG_DIR = PROJECT_ROOT / "logs"


def make_executor(cfg: Config):
    return TwakCliExecutor(cfg) if cfg.mode == "live" else PaperExecutor(cfg)


def run_once(cfg: Config, full_rebalance: bool | None = None) -> dict:
    """One agent cycle. Strategy rebalancing happens once a day (00:00 UTC);
    every other hourly run is a risk-only check so the drawdown ladder acts
    intraday instead of waiting for the next daily decision."""
    now = datetime.now(timezone.utc)
    if full_rebalance is None:
        full_rebalance = now.hour == 0

    feed = CmcClient(cfg.cmc_api_key)
    try:
        quotes = feed.quotes([REGIME_ANCHOR] + ALLOWLIST)
        fear_greed = feed.fear_greed()
    finally:
        feed.close()
    portfolio = Portfolio.load(STATE_DIR / f"{cfg.mode}_portfolio.json", cfg.paper_start_usdt)
    if cfg.mode == "live":
        sync_live_holdings(portfolio)
    # Stale-price fallback: a held asset missing from one feed response must
    # not be valued at zero (fake crash -> panicked risk engine).
    prices = portfolio.update_prices({s: q.price for s, q in quotes.items()})
    value, drawdown = portfolio.mark(prices)

    x402_proof = None
    if full_rebalance and cfg.x402_enabled:
        # Pay-per-request data in the trade loop (TWAK x402, $0.01/day). Used
        # as paid cross-check + audit proof, never as the sole decision input.
        x402_proof = fetch_quotes_x402([REGIME_ANCHOR])

    if full_rebalance:
        held = {s for s, q in portfolio.holdings.items() if s != BASE and q > 1e-12}
        decision = target_allocation(quotes, fear_greed, cfg, held)
    else:
        weights = portfolio.weights(prices)
        decision = Decision(
            exposure=sum(w for s, w in weights.items() if s != BASE),
            weights=weights,
            reasons=["hourly risk-only check (no strategy rebalance)"],
        )
    decision = risk.apply(decision, drawdown, cfg)

    orders = plan_orders(portfolio, prices, decision.weights, cfg)
    executor = make_executor(cfg)
    executed = sum(1 for o in orders if executor.execute(o, prices, portfolio))
    if executed:
        portfolio.record_trade()

    # Daily qualification trade (R3): mandatory during the live window.
    if cfg.mode == "live" and not portfolio.traded_today():
        micro = micro_qualification_order(cfg, portfolio, prices)
        if micro is not None and executor.execute(micro, prices, portfolio):
            portfolio.record_trade()
            log.info("daily qualification micro-trade executed")

    portfolio.save()

    summary = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": cfg.mode,
        "value_usd": round(value, 4),
        "drawdown": round(drawdown, 4),
        "fear_greed": fear_greed,
        "exposure": decision.exposure,
        "weights": {s: round(w, 4) for s, w in decision.weights.items()},
        "reasons": decision.reasons,
        "orders": [asdict(o) for o in orders],
        "orders_executed": executed,
        "holdings": {s: round(q, 8) for s, q in portfolio.holdings.items()},
        "x402": x402_proof,
    }
    _append_log(summary)
    return summary


def status(cfg: Config) -> dict:
    feed = CmcClient(cfg.cmc_api_key)
    try:
        quotes = feed.quotes(ALLOWLIST)
    finally:
        feed.close()
    prices = {s: q.price for s, q in quotes.items()}
    portfolio = Portfolio.load(STATE_DIR / f"{cfg.mode}_portfolio.json", cfg.paper_start_usdt)
    value = portfolio.value(prices)
    drawdown = 0.0 if portfolio.peak_value <= 0 else 1.0 - value / portfolio.peak_value
    return {
        "mode": cfg.mode,
        "value_usd": round(value, 4),
        "peak_usd": round(portfolio.peak_value, 4),
        "drawdown": round(drawdown, 4),
        "holdings": {s: round(q, 8) for s, q in portfolio.holdings.items()},
        "last_trade_date": portfolio.last_trade_date,
    }


def _append_log(entry: dict, path: Path | None = None) -> None:
    path = path or LOG_DIR / "agent.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
