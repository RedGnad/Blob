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

# Round-trip execution cost (%, USDT -> token -> USDT at $5 size). Measured via
# `blob costs` 2026-06-12 at the old 0.7%/side fee, then re-derived for the
# TWAK live-week fee waiver (0.7% -> 0.077%/side): the ~1.25pp provider-fee
# round-trip drop is subtracted, floored at the new fee, leaving each token's
# residual pool spread + slippage (which is what still separates majors from
# illiquid names like PENDLE). RE-MEASURE once the waiver is live on BSC.
RT_COST_PCT: dict[str, float] = {
    "ETH": 0.15, "AAVE": 0.15, "XRP": 0.15, "DOGE": 0.15, "CAKE": 0.15,
    "ATOM": 0.15, "LTC": 0.15, "AVAX": 0.15, "LINK": 0.32, "TWT": 0.33,
    "DOT": 0.33, "ADA": 0.48, "FLOKI": 0.64, "FET": 0.64, "PENDLE": 2.11,
}
DEFAULT_RT_COST_PCT = 0.30


def twak_token(symbol: str) -> str:
    """Token argument for TWAK CLI commands on BSC."""
    if symbol == BASE:
        return BASE
    return TOKENS.get(symbol, symbol)
