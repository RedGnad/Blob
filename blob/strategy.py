"""Deterministic decision core: regime filter + momentum selection.

Design constraints (docs/redteam.md):
- R4/R5: ~1.4% real round-trip cost floor -> only act on momentum that clears
  `min_momentum_pct`; low turnover by construction.
- R12: no LLM in the decision path; everything here is pure and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .datafeed import Quote
from .universe import ALLOWLIST, BASE, REGIME_ANCHOR


@dataclass(frozen=True)
class Decision:
    exposure: float                 # 0.0 / 0.5 / 1.0 fraction of NAV in risk assets
    weights: dict[str, float]       # target weights incl. BASE, sums to 1.0
    reasons: list[str] = field(default_factory=list)


def regime_exposure(quotes: dict[str, Quote], fear_greed: int, cfg: Config) -> tuple[float, list[str]]:
    """Market regime from the BTC anchor trend and Fear & Greed."""
    anchor = quotes.get(REGIME_ANCHOR)
    anchor_up = anchor is not None and anchor.pct_7d > 0
    sentiment_ok = fear_greed >= cfg.fg_risk_on
    reasons = [
        f"anchor {REGIME_ANCHOR} 7d {'+' if anchor_up else '-'}"
        + (f" ({anchor.pct_7d:.1f}%)" if anchor else " (missing)"),
        f"fear&greed {fear_greed} ({'>=' if sentiment_ok else '<'} {cfg.fg_risk_on})",
    ]
    if anchor_up and sentiment_ok:
        return 1.0, reasons + ["regime: risk-on"]
    if anchor_up or sentiment_ok:
        return 0.5, reasons + ["regime: mixed"]
    return 0.0, reasons + ["regime: risk-off"]


def momentum_score(q: Quote) -> float:
    return 0.4 * q.pct_24h + 0.6 * q.pct_7d


def select_candidates(
    quotes: dict[str, Quote], cfg: Config, held: set[str] = frozenset()
) -> list[Quote]:
    """Top-k allowlist assets whose momentum clears the cost-adjusted floor.

    Anti-churn hysteresis (R5), two mechanisms against the ~1.4% round-trip cost:
    - a held asset only needs the lower exit floor to stay eligible;
    - ranking gives held assets a retention bonus, so a challenger must beat
      them by `retention_bonus_pct`, not by a hair.
    """
    eligible = []
    for symbol in ALLOWLIST:
        if symbol not in quotes:
            continue
        floor = cfg.exit_momentum_pct if symbol in held else cfg.min_momentum_pct
        if momentum_score(quotes[symbol]) >= floor:
            eligible.append(quotes[symbol])

    def rank_score(q: Quote) -> float:
        return momentum_score(q) + (cfg.retention_bonus_pct if q.symbol in held else 0.0)

    eligible.sort(key=rank_score, reverse=True)
    return eligible[: cfg.top_k]


def target_allocation(
    quotes: dict[str, Quote], fear_greed: int, cfg: Config, held: set[str] = frozenset()
) -> Decision:
    exposure, reasons = regime_exposure(quotes, fear_greed, cfg)
    picks = select_candidates(quotes, cfg, held) if exposure > 0 else []

    anchor = quotes.get(REGIME_ANCHOR)
    if (
        cfg.fast_lane
        and len(picks) > 1
        and exposure == 1.0
        and anchor is not None
        and anchor.pct_7d >= cfg.fast_anchor_7d_pct
        and fear_greed >= cfg.fast_fg
    ):
        picks = picks[:1]
        reasons.append(f"fast lane: strong risk-on, concentrating on {picks[0].symbol}")
    if not picks:
        if exposure > 0:
            reasons.append(f"no candidate clears {cfg.min_momentum_pct:.1f}% momentum floor")
        return Decision(exposure=0.0, weights={BASE: 1.0}, reasons=reasons)

    per_asset = exposure / len(picks)
    weights = {q.symbol: per_asset for q in picks}
    weights[BASE] = 1.0 - exposure
    reasons += [
        f"pick {q.symbol} momentum {momentum_score(q):.1f}% -> weight {per_asset:.2f}"
        for q in picks
    ]
    return Decision(exposure=exposure, weights=weights, reasons=reasons)
