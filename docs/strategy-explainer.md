# Strategy explainer — Blob (DoraHacks submission text)

*Required by Track 1 submission: "Explain a bit the strategy so we can understand
how you achieved your results."*

## Thesis

A 7-day live PnL contest with a 30% drawdown disqualification gate and real
execution costs is not won by predicting the market — it is won by surviving it.
Public precedents (Alpha Arena season 1, where naive LLM traders finished between
-12% and -75%) show most autonomous agents destroy themselves through overtrading,
unbounded drawdowns, or operational failures. Blob's edge is engineered survival
plus disciplined momentum capture, with every parameter justified by measured
costs and competition-format backtests.

## Decision pipeline (deterministic, no LLM in the loop)

1. **Regime filter.** BTC 7-day trend and the CMC Fear & Greed index gate overall
   exposure: 100% risk-on when both agree, 50% when mixed, 0% (full USDT) when
   both are bearish. In a red week the agent parks in USDT and posts ~0% while
   momentum-chasing agents bleed or get disqualified.
2. **Cost-aware momentum selection.** Among a 15-token allowlist (vetted
   Binance-Peg majors from the 149 eligible tokens), rank by blended momentum
   (0.4 × 24h + 0.6 × 7d). A token may only enter the book if its momentum
   exceeds **twice its own measured round-trip execution cost** (we quoted every
   token at our trade size through TWAK: 1.27%–3.36%). Top-2 picks split the
   risk budget.
3. **Anti-churn hysteresis.** Held positions exit at a lower momentum floor than
   entries, and a challenger must beat a held asset by 2 points to displace it.
   This cut backtest turnover by ~30% — decisive when the cost floor is ~1.4%
   per rotation.
4. **Risk engine, applied after the strategy and before signing.** Drawdown
   ladder on hourly marks: -10% halves exposure, -18% flattens to USDT (the
   official DQ gate is ~30%; we never get near it — 0 disqualified windows in
   358 backtested). Token allowlist and balance clamps are enforced here too.
5. **Cadence.** Full strategy rebalance once a day at 00:00 UTC; every other
   hour is a risk-only check so the ladder acts intraday. The mandatory daily
   trade is guaranteed by a buffered micro-trade (buy with base, or sell a
   sliver when fully deployed) retried every hour until confirmed.

## Execution

TWAK is the sole execution layer: local signing, slippage-capped swaps on BSC,
holdings re-synced from the chain every cycle. The daily rebalance pays for its
CMC data through the x402 endpoint ($0.01 per request in USDT via Permit2 on
BSC) and cross-checks it against the free feed. The agent carries an ERC-8004
on-chain identity (agentId 132858) owned by the trading wallet.

## What the backtest says (and does not say)

358 independent 7-day windows over a bear year (ETH -42%): median -1.7%,
p90 +6.7%, best +20.6%, zero disqualifications, worst drawdown 21.5%. We do not
claim a magic alpha over one week — we claim a distribution with a protected
left tail and an open right tail, in a field where the left tail eliminates
competitors.
