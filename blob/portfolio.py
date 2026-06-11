"""Portfolio state: holdings, valuation, peak tracking, drawdown.
State is persisted as JSON under state/ (gitignored)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .universe import BASE


@dataclass
class Portfolio:
    holdings: dict[str, float]          # symbol -> quantity (BASE quantity ~= USD)
    peak_value: float
    last_trade_date: str = ""           # UTC date of last executed trade (R3 daily rule)
    last_rebalance_date: str = ""       # UTC date of last full strategy rebalance
    last_prices: dict[str, float] = field(default_factory=dict)
    path: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, path: Path, start_usdt: float) -> "Portfolio":
        if path.exists():
            raw = json.loads(path.read_text())
            return cls(
                holdings=raw["holdings"],
                peak_value=raw["peak_value"],
                last_trade_date=raw.get("last_trade_date", ""),
                last_rebalance_date=raw.get("last_rebalance_date", ""),
                last_prices=raw.get("last_prices", {}),
                path=path,
            )
        return cls(holdings={BASE: start_usdt}, peak_value=start_usdt, path=path)

    def save(self) -> None:
        assert self.path is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "holdings": self.holdings,
            "peak_value": self.peak_value,
            "last_trade_date": self.last_trade_date,
            "last_rebalance_date": self.last_rebalance_date,
            "last_prices": self.last_prices,
        }, indent=2))

    def update_prices(self, fresh: dict[str, float]) -> dict[str, float]:
        """Merge fresh prices over the last known ones. A held asset whose
        price is missing from one feed response must NOT be valued at zero —
        that would fake a crash and panic the risk engine; we fall back to
        its last known price instead."""
        self.last_prices.update({s: p for s, p in fresh.items() if p})
        return dict(self.last_prices)

    def value(self, prices: dict[str, float]) -> float:
        total = 0.0
        for symbol, qty in self.holdings.items():
            price = 1.0 if symbol == BASE else prices.get(symbol, 0.0)
            total += qty * price
        return total

    def mark(self, prices: dict[str, float]) -> tuple[float, float]:
        """Returns (value, drawdown) and updates the peak."""
        value = self.value(prices)
        self.peak_value = max(self.peak_value, value)
        drawdown = 0.0 if self.peak_value <= 0 else 1.0 - value / self.peak_value
        return value, drawdown

    def weights(self, prices: dict[str, float]) -> dict[str, float]:
        """Current portfolio weights (BASE included)."""
        total = self.value(prices)
        if total <= 0:
            return {BASE: 1.0}
        out: dict[str, float] = {}
        for symbol, qty in self.holdings.items():
            price = 1.0 if symbol == BASE else prices.get(symbol, 0.0)
            out[symbol] = qty * price / total
        out.setdefault(BASE, 0.0)
        return out

    def traded_today(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return self.last_trade_date == now.date().isoformat()

    def record_trade(self, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        self.last_trade_date = now.date().isoformat()
