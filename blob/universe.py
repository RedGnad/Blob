"""Tradeable universe: a vetted, liquid subset of the 149 eligible BEP-20
tokens (competition rules). Restricting to majors is both a risk guardrail
(transfer-tax / illiquid traps in the full list, see docs/redteam.md R7) and
a cost control (AMM slippage).

TOKENS maps each CMC symbol to the argument the TWAK CLI needs on BSC:
the plain symbol when TWAK's registry knows it natively, otherwise the
Binance-Peg contract address (TWAK returns TOKEN_NOT_FOUND for symbols
outside its registry — live-verified). Contracts were resolved through
`twak search` on 2026-06-12 and sanity-checked against Binance spot prices
(all deviations < 1.1%). UNI, FIL and SHIB have no BSC entry in the TWAK
registry and were dropped.
"""

BASE = "USDT"

# Regime anchor only — BTC is NOT in the eligible list and is never traded.
REGIME_ANCHOR = "BTC"

TOKENS: dict[str, str] = {
    # natively known by the TWAK registry (quoted fine by symbol)
    "ETH": "ETH",
    "DOGE": "DOGE",
    "LTC": "LTC",
    "AVAX": "AVAX",
    "ATOM": "ATOM",
    "TWT": "TWT",
    # resolved to Binance-Peg contracts via twak search
    "XRP": "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE",
    "ADA": "0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47",
    "LINK": "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",
    "DOT": "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402",
    "AAVE": "0xfb6115445Bff7b52FeB98650C87f44907E58f802",
    "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
    "FET": "0x031b41e504677879370e9DBcF937283A8691Fa7f",
    "PENDLE": "0xb3Ed0A426155B79B898849803E3B36552f7ED507",
    "FLOKI": "0xfb5B838b6cfEEdC2873aB27866079AC55363D37E",
}

ALLOWLIST = list(TOKENS)

# Measured round-trip execution cost (%, USDT -> token -> USDT at $5 size,
# `blob costs`, 2026-06-12). Drives the cost-aware entry floor in strategy.py.
RT_COST_PCT: dict[str, float] = {
    "ETH": 1.27, "AAVE": 1.28, "XRP": 1.33, "DOGE": 1.37, "CAKE": 1.37,
    "ATOM": 1.38, "LTC": 1.39, "AVAX": 1.40, "LINK": 1.57, "TWT": 1.58,
    "DOT": 1.58, "ADA": 1.73, "FLOKI": 1.89, "FET": 1.89, "PENDLE": 3.36,
}
DEFAULT_RT_COST_PCT = 1.5


def twak_token(symbol: str) -> str:
    """Token argument for TWAK CLI commands on BSC."""
    if symbol == BASE:
        return BASE
    return TOKENS.get(symbol, symbol)
