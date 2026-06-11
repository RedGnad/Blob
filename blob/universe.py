"""Tradeable universe: a vetted, liquid subset of the 149 eligible BEP-20
tokens (competition rules). Restricting to majors is both a risk guardrail
(transfer-tax / illiquid traps in the full list, see docs/redteam.md R7) and
a cost control (AMM slippage).

TODO before the live week: verify Binance-Peg liquidity on PancakeSwap for
each symbol and prune anything with a thin pool.
"""

BASE = "USDT"

# Regime anchor only — BTC is NOT in the eligible list and is never traded.
REGIME_ANCHOR = "BTC"

ALLOWLIST = [
    "ETH",
    "XRP",
    "DOGE",
    "ADA",
    "LINK",
    "LTC",
    "AVAX",
    "DOT",
    "UNI",
    "AAVE",
    "ATOM",
    "FIL",
    "CAKE",
    "TWT",
    "FET",
    "PENDLE",
    "FLOKI",
    "SHIB",
]
