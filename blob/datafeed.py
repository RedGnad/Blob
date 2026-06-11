"""CoinMarketCap data client (Basic/free plan endpoints only).

Endpoints used:
- /v2/cryptocurrency/quotes/latest  (prices + 1h/24h/7d momentum)
- /v3/fear-and-greed/latest         (regime input; neutral fallback on error)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://pro-api.coinmarketcap.com"
NEUTRAL_FEAR_GREED = 50


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    pct_1h: float
    pct_24h: float
    pct_7d: float
    market_cap: float


class CmcClient:
    def __init__(self, api_key: str, timeout: float = 20.0):
        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=timeout,
            headers={"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"},
        )

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        resp = self._client.get(
            "/v2/cryptocurrency/quotes/latest",
            params={"symbol": ",".join(symbols), "convert": "USD"},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        out: dict[str, Quote] = {}
        for symbol, matches in data.items():
            if not isinstance(matches, list):
                matches = [matches]
            # Symbol collisions exist on CMC; keep the highest-cap active match.
            candidates = [
                m for m in matches
                if m.get("is_active", 1) and m.get("quote", {}).get("USD", {}).get("price")
            ]
            if not candidates:
                log.warning("no active quote for %s", symbol)
                continue
            best = max(
                candidates,
                key=lambda m: m["quote"]["USD"].get("market_cap") or 0,
            )
            usd = best["quote"]["USD"]
            out[symbol] = Quote(
                symbol=symbol,
                price=float(usd["price"]),
                pct_1h=float(usd.get("percent_change_1h") or 0.0),
                pct_24h=float(usd.get("percent_change_24h") or 0.0),
                pct_7d=float(usd.get("percent_change_7d") or 0.0),
                market_cap=float(usd.get("market_cap") or 0.0),
            )
        return out

    def fear_greed(self) -> int:
        try:
            resp = self._client.get("/v3/fear-and-greed/latest")
            resp.raise_for_status()
            return int(resp.json()["data"]["value"])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            log.warning("fear & greed unavailable (%s), using neutral %d", exc, NEUTRAL_FEAR_GREED)
            return NEUTRAL_FEAR_GREED

    def close(self) -> None:
        self._client.close()
