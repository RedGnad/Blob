# Blob — trading strategy (full description)

Agent: `0x84BFC511d8027337B285433f122880fB340f30B9` (BSC mainnet, registered for the
competition). Track 1 is scored on live PnL over June 22–28 with a 30% max-drawdown
disqualification gate, a ≥1-trade/day rule, and simulated transaction costs.

This is the complete strategy, written for review. Nothing here is secret — Track 1
is a PnL contest (others can't beat us by reading this), and the repo is public.

## 1. Thesis

A 7-day live PnL contest with a hard DQ gate is not won by predicting the market —
it is won by **surviving it while capturing the upside that exists**. Public
precedents (Alpha Arena S1: naive LLM traders finished -12% to -75%) show most
autonomous agents self-destruct via overtrading, unbounded drawdown, or operational
failure. Blob's edge is engineered survival + disciplined momentum capture, every
parameter justified by measured costs and competition-format backtests. We do **not**
claim alpha; we claim a return distribution with a protected left tail and an open
right tail, in a field where the left tail eliminates competitors.

## 2. Decision pipeline (deterministic, no LLM in the loop)

Runs once a day (00:00 UTC) for the full strategy decision; every other hour is a
risk-only check so the drawdown ladder reacts intraday.

1. **Regime filter** — two gates set total risk exposure:
   - BTC 7-day trend (BTC is the anchor signal only; it is **not** in the tradeable
     set, never traded).
   - CMC Fear & Greed index vs a threshold (35).
   - Both bullish → 100% risk-on. One → 65% (mixed). Neither → 0% (all USDT).
   In a red week the agent parks in USDT and posts ~0% while momentum-chasers bleed.

2. **Cost-aware momentum selection** — among a 15-token allowlist (vetted
   Binance-Peg majors from the 149 eligible BEP-20 tokens; illiquid/transfer-tax
   names excluded), rank by blended momentum `0.4·(24h%) + 0.6·(7d%)`. A token may
   enter only if its momentum clears **2× its own measured round-trip execution
   cost**. Top-2 picks split the risk budget.

3. **Anti-churn hysteresis** — a held position exits at a lower momentum floor than
   entries, and a challenger must beat a held asset by 2 points to displace it. This
   cut backtest turnover ~30% — decisive against the per-rotation cost floor.

4. **Risk engine (applied after the strategy, before signing)** — drawdown ladder on
   hourly equity marks: **−10% halves exposure, −16% flattens to USDT**. The official
   DQ gate is 30% (confirmed by organizers); this self-caps the worst observed window
   drawdown at ~20% — a 10-point safety margin. Token allowlist and per-trade /
   daily-count caps are enforced here too.

5. **Daily-trade guarantee** — the contest requires ≥1 trade/day (7/week); a day in
   cash = DQ. When the strategy doesn't trade (e.g. risk-off), a minimum **qualifying
   micro-trade** fires, preferring to trim an existing holding so it never builds
   exposure the strategy didn't ask for. Retried every hour until it lands.

## 3. Calibration — how the parameters were chosen

Three calibrations (defensive / moderate / return-seeking) were backtested on **358
independent 7-day windows** (fresh capital and drawdown peak per window — exactly the
contest format). **Moderate** was selected: it is the efficient-frontier point,
capturing upside (higher p90 / max) while keeping a wide DQ margin and 0% DQ. A
`fast_lane` variant (single-asset concentration) was rejected as **overfit** — its
entire apparent edge came from a single 2-day pump (2 of 358 windows), and it was
worse on the median and p90.

The kill-switch was then hardened (−16% flatten) because it costs almost nothing in
return (−0.2pt median, identical p90/max) but caps worst-case drawdown at ~20%.
DQ = total loss, so that insurance dominates a fraction of a point of upside.

## 4. Execution cost re-tune (TWAK live-week fee waiver)

The organizers cut the TWAK execution fee from 0.7% to 0.077% per side for the live
week (≈10×). We re-derived per-token round-trip costs and lowered the cost-aware
entry floor accordingly. Effect on the moderate calibration (backtest, a year where
ETH did −42%): **median −1.8% → −0.2%, p90 +8.9% → +11.0%, max +28.3% → +30.0%,
share of positive windows 25% → 33%, still 0% DQ.** A finding worth noting: lowering
the activity threshold further does **not** help — the gain comes from the same trades
bleeding ~10× less, not from more trades. We kept the threshold conservative.

## 5. Backtest results (competition format, keyless, reproducible)

358 windows, bear year (ETH −42%), measured costs, hourly marks:

| Metric (7-day windows) | Value |
|---|---|
| Median | −0.4% |
| p90 / max | +10.8% / +30.0% |
| Share of positive windows | 33% |
| Disqualification rate (30% DD) | **0%** |
| Worst window drawdown | 20.0% |

Reproduce with no API key: `python -m blob backtest --days 365` (public Binance
klines + Fear & Greed history, replaying the exact production decision code).

## 6. Honest limitations (what a reviewer should push on)

- **No median alpha in a bear backtest.** With more exposure you lose more in a
  downtrend — mathematical. We choose distribution *shape* (protected left tail, open
  right tail), not magic. If the live week is strongly bearish, even moderate ends
  slightly negative; then survival + a DQ-heavy field carry our rank.
- **One-week sample.** The live regime is a single unknown draw. We can't predict it;
  we can only avoid blowing up and capture upside if it appears.
- **Backtest cost model** assumes a flat per-side cost; the organizers' exact
  *simulated* cost model is unconfirmed, so we keep the entry threshold conservative
  (robust to any model).
- **Field edge, not pure alpha.** Part of our expected rank comes from a weak field
  (many competitors reportedly can't even execute swaps). That's real but external.

## 7. What a reviewer might suggest (open questions for the trader friend)

- Is the 0.4/0.6 (24h/7d) momentum blend the right horizon for a 1-week hold?
- Is top-2 the right concentration, or would top-3 / vol-weighting improve the
  risk-adjusted return?
- Is the −10%/−16% ladder well-placed given the 30% gate now confirmed, or is there
  free upside in loosening slightly?
- Would a volatility-targeting overlay (size by realized vol) beat fixed exposure
  tiers?
