"""7-day survival: the failure modes that could cost the $10k (a missed daily
trade = DQ). These test the load-bearing reliability mechanisms directly."""

from pathlib import Path

import blob.scheduler as scheduler
from blob.config import Config
from blob.portfolio import Portfolio
from blob.universe import BASE

CFG = Config(cmc_api_key="test")


def test_scheduler_retries_then_succeeds(monkeypatch):
    """A transient failure (RPC/API hiccup) must not lose the cycle: retry."""
    monkeypatch.setattr(scheduler.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def flaky(_cfg):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient RPC error")
        return {"value_usd": 15.0, "drawdown": 0.0, "orders_executed": 0}

    monkeypatch.setattr(scheduler, "run_once", flaky)
    assert scheduler.run_cycle_with_retries(CFG) is True
    assert calls["n"] == 3


def test_scheduler_alerts_on_total_failure(monkeypatch):
    """If every attempt fails, the loop survives (returns False) and alerts —
    it must never crash the 7-day runner."""
    monkeypatch.setattr(scheduler.time, "sleep", lambda *_: None)
    alerts = []
    monkeypatch.setattr(scheduler, "notify", lambda msg: alerts.append(msg))
    monkeypatch.setattr(scheduler, "run_once", lambda _cfg: (_ for _ in ()).throw(RuntimeError("down")))
    assert scheduler.run_cycle_with_retries(CFG) is False
    assert len(alerts) == 1


def test_state_survives_restart(tmp_path: Path):
    """Clean restart: portfolio state must round-trip exactly (a cloud runner
    restores it from the agent-state branch every cycle)."""
    path = tmp_path / "live_portfolio.json"
    pf = Portfolio.load(path, start_usdt=15.0)
    pf.holdings = {BASE: 7.5, "ETH": 0.002}
    pf.peak_value = 18.3
    pf.last_trade_date = "2026-06-22"
    pf.last_rebalance_date = "2026-06-22"
    pf.record_swap()
    pf.last_prices = {"ETH": 1800.0}
    pf.save()

    restored = Portfolio.load(path, start_usdt=15.0)
    assert restored.holdings == {BASE: 7.5, "ETH": 0.002}
    assert restored.peak_value == 18.3
    assert restored.last_trade_date == "2026-06-22"
    assert restored.last_rebalance_date == "2026-06-22"
    assert restored.last_prices == {"ETH": 1800.0}
    assert restored.swaps_today == pf.swaps_today


def test_drawdown_unaffected_by_missing_prices_after_restart(tmp_path: Path):
    """A feed gap right after restart must not fake a crash: last-known prices
    persist and value stays sane."""
    path = tmp_path / "live_portfolio.json"
    pf = Portfolio.load(path, start_usdt=15.0)
    pf.holdings = {BASE: 5.0, "ETH": 0.005}
    pf.update_prices({"ETH": 2000.0})  # value = 5 + 10 = 15
    pf.save()
    restored = Portfolio.load(path, start_usdt=15.0)
    prices = restored.update_prices({})  # feed returns nothing this cycle
    value, drawdown = restored.mark(prices)
    assert abs(value - 15.0) < 1e-9
    assert drawdown == 0.0
