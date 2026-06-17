"""The >=1-trade/day rule (7 over the week) is a DQ vector the defensive
hardening makes WORSE: an agent that sits in cash on a bear day makes <7 trades
and loses the $10k by own-goal. This proves a qualifying trade lands every day
even through a 7-day risk-off regime where the strategy wants 0% exposure."""

import datetime as dt

import blob.agent as agent
from blob.config import Config
from blob.datafeed import Quote
from blob.portfolio import Portfolio


class FakeBearFeed:
    """Everything bearish -> risk-off regime, zero momentum candidates ->
    strategy wants 100% cash, so it never rebalances on its own."""

    def __init__(self, *a, **k):
        pass

    def quotes(self, symbols):
        return {s: Quote(symbol=s, price=100.0, pct_1h=-0.5, pct_24h=-3.0,
                         pct_7d=-8.0, market_cap=1e9) for s in symbols}

    def fear_greed(self):
        return 10  # extreme fear

    def close(self):
        pass


def test_bear_week_still_makes_seven_trades(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "CmcClient", FakeBearFeed)
    monkeypatch.setattr(agent, "STATE_DIR", tmp_path)
    monkeypatch.setattr(agent, "LOG_DIR", tmp_path)

    class FakeDT:
        current = dt.datetime(2026, 6, 22, 0, 5, tzinfo=dt.timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr(agent, "datetime", FakeDT)
    cfg = Config(cmc_api_key="test", mode="paper")

    traded_days = 0
    for day in range(22, 29):  # June 22..28, the live window
        FakeDT.current = dt.datetime(2026, 6, day, 0, 5, tzinfo=dt.timezone.utc)
        summary = agent.run_once(cfg)
        assert summary["exposure"] == 0.0  # strategy genuinely wants cash
        pf = Portfolio.load(tmp_path / "paper_portfolio.json", cfg.paper_start_usdt)
        if pf.last_trade_date == f"2026-06-{day:02d}":
            traded_days += 1

    assert traded_days == 7  # qualifying trade every single day despite 0% exposure


def test_capital_stays_above_dust_through_bear_week(tmp_path, monkeypatch):
    """Sub-$1 portfolio at the top of an hour scores 0%. The qualifying trades
    must never drain the wallet to dust."""
    monkeypatch.setattr(agent, "CmcClient", FakeBearFeed)
    monkeypatch.setattr(agent, "STATE_DIR", tmp_path)
    monkeypatch.setattr(agent, "LOG_DIR", tmp_path)

    class FakeDT:
        current = dt.datetime(2026, 6, 22, 0, 5, tzinfo=dt.timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr(agent, "datetime", FakeDT)
    cfg = Config(cmc_api_key="test", mode="paper")

    for day in range(22, 29):
        FakeDT.current = dt.datetime(2026, 6, day, 0, 5, tzinfo=dt.timezone.utc)
        summary = agent.run_once(cfg)
        assert summary["value_usd"] > 10.0  # nowhere near the $1 dust floor
