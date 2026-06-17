# Blob 🫧

> **A self-custody trading agent that commits every decision on-chain and sells its signal through a trustless escrow — verify it all yourself in 30 seconds.**

Built for [BNB Hack: AI Trading Agent Edition](https://dorahacks.io/hackathon/bnbhack-twt-cmc) (CoinMarketCap × Trust Wallet × BNB Chain). Trades live on BSC with self-custody signing (keys never leave Trust Wallet Agent Kit), reads CoinMarketCap through MCP + x402, and carries a first-class ERC-8004 identity. Most agents die in week one — drawdown DQ, overtrading, a missed mandatory trade. Blob is engineered around the opposite premise: **in a 7-day live PnL contest, not blowing up is the highest-EV strategy.**

**Who it's for:** a self-custody holder who wants disciplined, automated market exposure **without handing their keys to a bot or an exchange.** You set the rules — drawdown caps, token allowlist, trade size limits — the agent executes them unattended and proves every move on-chain. It's not a fund or a signal group you trust; it's code you run, configure, and verify yourself.

## ✅ Verify everything yourself in 30 seconds

```bash
python verify.py        # recompute our on-chain decision digest — no key, no trust
```

It reproduces, locally, the SHA-256 that Blob committed on-chain for a real trading decision, and prints the exact transactions to check. If the numbers match, the agent fabricated nothing. Same guarantee for the alpha it sells: `python bnb-sdk-demo/signal.py`.

## On-chain proof (everything below is real, BSC mainnet)

| Claim | Proof |
|---|---|
| Agent wallet (self-custody, TWAK-created) | [`0x84BFC511d8027337B285433f122880fB340f30B9`](https://bscscan.com/address/0x84BFC511d8027337B285433f122880fB340f30B9) |
| Competition registration | [`0x9bfc02…ae0fbc`](https://bscscan.com/tx/0x9bfc02ddef61a097061afe9a1014b43e20fb13b64b6d72cd129e7004f6ae0fbc) |
| TWAK swap execution, buy leg | [`0x080ddd…90b877`](https://bscscan.com/tx/0x080ddda1faa6e9564c548874d862daeb697748874233e6190f24a4abbd90b877) |
| TWAK swap execution, sell leg | [`0xeda75e…2ae4c0`](https://bscscan.com/tx/0xeda75e7a880d193e6c6fa81dff37e982a32a6cd8d766205867f14159982ae4c0) |
| x402 pay-per-request data (Permit2 approval; $0.01 USDT per request, paid on BSC) | [`0x2b6888…397bfd`](https://bscscan.com/tx/0x2b688866ea909e29aa3d03792146210df5157c314060579727fc866f7d397bfd) |
| ERC-8004 agent identity, `agentId 132858`, owned by the trading wallet | [`0x14a6f4…a25103`](https://bscscan.com/tx/0x14a6f4c62986e60aaed77b3cfc7dafd41ef0b9814d6365c33531f8a4c7a25103) |
| On-chain decision attestation (digest committed as ERC-8004 metadata) | [`0xc9460f…c23b07`](https://bscscan.com/tx/0xc9460f77e6e61ba08fd7ddd8d9a67d46a973ae39abe76a5949349f480ac23b07) |
| Hourly audit trail (every decision, order and x402 payment) | [`agent-state` branch](https://github.com/RedGnad/Blob/tree/agent-state) |

## How it works

```
CMC market data ──────────► strategy: regime filter (BTC trend + Fear&Greed)
 (API key feed +                      + cost-aware momentum selection
  x402 pay-per-request                      │
  in the trade loop)                        ▼
                              risk engine — last gate before signing:
                              drawdown ladder (-10% halve / -18% flatten,
                              official DQ is ~30%), token allowlist,
                              balance clamps, daily-trade guarantee
                                            │
                                            ▼
                              TWAK — sole execution layer:
                              local signing, swaps, x402, ERC-8004
                              (keys never leave the wallet store)
```

- **Deterministic core.** No LLM in the decision path: regime and momentum rules are pure functions with 33 unit tests. Reproducible, auditable, no nondeterministic blow-ups.
- **Hourly risk / daily strategy split.** Strategy rebalances once a day (00:00 UTC); every other hour is a risk-only check so the drawdown ladder acts intraday. Backtest before this fix: 1 window in 358 hit the 30% DQ. After: zero, worst window 21.5%.
- **Cost-aware entries.** Real round-trip execution costs were measured per token at our trade size via TWAK quotes (`blob costs`): 1.27%–1.89%, median 1.4%, PENDLE 3.36%. A token only enters the book if its momentum clears **2× its own measured round-trip cost**. Anti-churn hysteresis (exit floor + retention bonus) cut turnover ~30%.
- **Qualification is engineered, not hoped for.** The competition requires ≥1 trade/day. Any successful cycle of the day fires a buffered micro-trade if the strategy was idle — including selling a sliver when fully deployed. Up to 23 retry opportunities per day via the hourly scheduler.
- **The chain is the truth.** In live mode, holdings are re-synced from BSC every cycle; prices fall back to last-known on feed gaps (a missing price must never look like a crash).
- **Tamper-evident decisions.** Each daily decision is hashed (SHA-256 of its canonical JSON) and committed on-chain as metadata on the agent's own ERC-8004 identity. Anyone can take a decision from the audit log, recompute the digest, and check it against the chain — a recompute-it-yourself track record that proves the decisions weren't fabricated after the fact. Verify: `twak erc8004 get-metadata 132858 --key d-<UTC-date> --chain bsc`.

## Backtest — competition format, not vanity curves

358 independent 7-day windows (fresh capital, fresh drawdown peak — exactly how the contest scores), hourly marks, measured costs, over a year where ETH buy-and-hold did **-42%**:

| Metric (7-day windows) | Blob |
|---|---|
| Median | -1.7% |
| p90 / max | +6.7% / +20.6% |
| Disqualification rate (30% DD) | **0%** |
| Worst window drawdown | 21.5% |
| Avg trades per window | 6.3 |

Run it yourself, no API key needed: `python -m blob backtest --days 365` (public Binance klines + Fear & Greed history, replaying the exact production decision code).

## Sponsor stack — used as the heart, not bolted on

- **Trust Wallet Agent Kit**: sole execution layer. Local signing through the whole loop (keys created by and stored in TWAK, password in OS keychain / `TWAK_WALLET_PASSWORD` headless), swaps with slippage caps, **native x402** paying $0.01 per data request from the trading balance (BSC, Permit2), **ERC-8004 identity** minted and owned by the trading wallet itself.
- **CoinMarketCap AI Agent Hub**: the data backbone of every decision, used across **multiple Hub surfaces**:
  - **Quotes** (`/v2/cryptocurrency/quotes/latest`) and the **Fear & Greed index** (`/v3/fear-and-greed/latest`) drive the regime filter and momentum ranking.
  - **x402 pay-per-request** on **two distinct Hub endpoints** in the trade loop, paid in USDT on BSC via Permit2 — a quotes cross-check *and* a `listings/latest` market-breadth snapshot ($0.01 each, real on-chain payments, logged to the audit trail). Not a README mention: see the `x402` field in [`agent-state`](https://github.com/RedGnad/Blob/tree/agent-state).
  - **Robustness for agent consumption**: v3 responses are a list per ticker, so we filter to active tokens by market cap (guards against memecoins squatting major symbols) and cross-check the x402 price against the keyed feed, flagging divergence.
- **BNB Chain**: all execution, registration, identity and payments settle on BSC.

## Run your own Blob

Blob is the product: clone it, point it at your own self-custody wallet, set your risk appetite, and deploy it for free. Three steps.

**1. Install & connect your wallet**
```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env          # your CMC key + your TWAK credentials (keys stay in TWAK)
.venv/bin/python -m blob doctor       # config check (never prints secrets)
```

**2. Set your own risk limits** — edit `blob/config.py` (all guardrails are yours to dial):

| Knob | What it controls |
|---|---|
| `dd_half` / `dd_kill` | drawdown ladder — halve / flatten to cash |
| `max_trade_fraction` / `max_trades_per_day` | per-trade size & daily trade caps |
| `mixed_exposure`, `top_k`, `min_momentum_pct` | how aggressive / concentrated |
| `ALLOWLIST` (`blob/universe.py`) | which tokens it may ever touch |

```bash
.venv/bin/python -m blob backtest --days 365   # see your settings on 358 windows, keyless
.venv/bin/python -m blob run-once              # one cycle (paper by default)
```

**3. Deploy it (free)** — push to a private repo and the included GitHub Actions workflow (`.github/workflows/agent.yml`) runs it 24/7 with self-healing and email alerts; state persists on the `agent-state` branch. A local runner (`blob loop` / `ops/`) is the warm backup. Flip live with one variable: `AGENT_MODE=live`. No server to rent, no keys to surrender.

**Status:** dress-rehearsal (paper, 24/7, cloud + local) until the trading window opens June 22; live trading June 22–28. Strategy write-up: [docs/strategy.md](docs/strategy.md).

**Status:** dress-rehearsal (paper, 24/7, cloud + local) until the trading window opens June 22; live trading June 22–28. Strategy write-up: [docs/strategy-explainer.md](docs/strategy-explainer.md).
