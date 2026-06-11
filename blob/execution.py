"""Order planning and executors.

- plan_orders: hysteresis-based rebalancing (R5: don't churn the cost floor).
- PaperExecutor: simulated fills with the measured ~0.7%/side cost.
- TwakCliExecutor: live execution through the TWAK CLI — the sole execution
  layer for the TWAK special prize. UNTESTED until the CLI is installed; the
  exact flags must be verified against `twak --help` before the live week.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass

from .config import Config
from .portfolio import Portfolio
from .universe import ALLOWLIST, BASE

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Order:
    side: str        # "buy" (BASE -> symbol) or "sell" (symbol -> BASE)
    symbol: str
    usd_amount: float


def plan_orders(
    portfolio: Portfolio,
    prices: dict[str, float],
    target_weights: dict[str, float],
    cfg: Config,
) -> list[Order]:
    total = portfolio.value(prices)
    if total <= 0:
        return []
    orders: list[Order] = []
    symbols = set(portfolio.holdings) | set(target_weights)
    symbols.discard(BASE)
    threshold = max(cfg.min_trade_usd, cfg.rebalance_fraction * total)
    for symbol in sorted(symbols):
        price = prices.get(symbol)
        if not price:
            continue
        current_usd = portfolio.holdings.get(symbol, 0.0) * price
        target_usd = target_weights.get(symbol, 0.0) * total
        delta = target_usd - current_usd
        if abs(delta) < threshold:
            continue
        side = "buy" if delta > 0 else "sell"
        orders.append(Order(side=side, symbol=symbol, usd_amount=abs(delta)))
    # Free up BASE first.
    orders.sort(key=lambda o: o.side != "sell")
    return orders


def micro_qualification_order(
    cfg: Config, portfolio: Portfolio, prices: dict[str, float]
) -> Order | None:
    """Minimum-size trade to satisfy the 1-trade/day rule (R3) when the
    strategy has nothing to do. Qualification constraint, not a scoring lever.

    Buys with BASE when available; when fully deployed (no BASE left), sells a
    sliver of the largest holding instead — failing the daily trade means
    disqualification, so this path must always produce an order if any value
    is tradable. The 10% buffer and the 1.5x reserve requirement keep us off
    the exact limit (slippage, price drift between quote and execution)."""
    amount = round(cfg.min_trade_usd * 1.1, 2)
    if portfolio.holdings.get(BASE, 0.0) >= amount * 1.5:
        return Order(side="buy", symbol="ETH", usd_amount=amount)
    largest, largest_usd = None, 0.0
    for symbol, qty in portfolio.holdings.items():
        if symbol == BASE:
            continue
        usd = qty * prices.get(symbol, 0.0)
        if usd > largest_usd:
            largest, largest_usd = symbol, usd
    if largest and largest_usd >= amount * 1.5:
        return Order(side="sell", symbol=largest, usd_amount=amount)
    log.error("cannot build qualification trade: portfolio too small")
    return None


def sync_live_holdings(portfolio: Portfolio) -> bool:
    """Replace local holdings with on-chain reality (live mode only). Local
    tracking after a real swap is approximate; the chain is the truth the
    competition scores. On failure keeps local state and returns False."""
    try:
        result = subprocess.run(
            ["twak", "wallet", "portfolio", "--chains", "bsc", "--json"],
            capture_output=True, text=True, timeout=60,
        )
        rows = json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        log.warning("live holdings sync failed, keeping local state: %s", exc)
        return False
    holdings = {BASE: 0.0}
    for row in rows:
        symbol = row.get("symbol")
        if symbol == BASE or symbol in ALLOWLIST:
            holdings[symbol] = float(row.get("balance") or 0.0)
    portfolio.holdings = holdings
    return True


class PaperExecutor:
    def __init__(self, cfg: Config):
        self.cost_per_side = cfg.cost_per_side

    def execute(self, order: Order, prices: dict[str, float], portfolio: Portfolio) -> bool:
        price = prices.get(order.symbol)
        if not price:
            log.warning("paper: no price for %s, skipping", order.symbol)
            return False
        base = portfolio.holdings.get(BASE, 0.0)
        if order.side == "buy":
            spend = min(order.usd_amount, base)
            if spend <= 0:
                log.warning("paper: no %s left to buy %s", BASE, order.symbol)
                return False
            qty = (spend / price) * (1.0 - self.cost_per_side)
            portfolio.holdings[BASE] = base - spend
            portfolio.holdings[order.symbol] = portfolio.holdings.get(order.symbol, 0.0) + qty
        else:
            held_qty = portfolio.holdings.get(order.symbol, 0.0)
            qty = min(order.usd_amount / price, held_qty)
            if qty <= 0:
                log.warning("paper: no %s to sell", order.symbol)
                return False
            proceeds = qty * price * (1.0 - self.cost_per_side)
            portfolio.holdings[order.symbol] = held_qty - qty
            portfolio.holdings[BASE] = base + proceeds
        # Drop dust entries so valuation stays clean; BASE always stays.
        portfolio.holdings = {
            s: q for s, q in portfolio.holdings.items() if s == BASE or q > 1e-12
        }
        log.info("paper fill: %s %s $%.2f", order.side, order.symbol, order.usd_amount)
        return True


class TwakCliExecutor:
    """Live execution via `twak swap` from the registered agent wallet.

    Syntax verified against twak 0.18.0 (quote path tested on BSC; execution
    path still untested with funds). The wallet password is resolved by twak
    itself from the OS keychain or TWAK_WALLET_PASSWORD — never passed in argv.
    """

    def __init__(self, cfg: Config):
        if shutil.which("twak") is None:
            raise RuntimeError(
                "twak CLI not found. Install it from portal.trustwallet.com before MODE=live."
            )
        self.cfg = cfg

    def execute(self, order: Order, prices: dict[str, float], portfolio: Portfolio) -> bool:
        src, dst = (BASE, order.symbol) if order.side == "buy" else (order.symbol, BASE)
        cmd = ["twak", "swap", src, dst, "--usd", f"{order.usd_amount:.2f}",
               "--chain", "bsc", "--slippage", "1", "--json"]
        log.info("twak: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            log.error("twak swap failed: %s", result.stderr.strip()[:500])
            return False
        log.info("twak swap ok: %s", result.stdout.strip()[:500])
        return True
