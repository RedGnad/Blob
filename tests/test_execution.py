from blob.config import Config
from blob.execution import (
    Order,
    PaperExecutor,
    clamp_order_usd,
    micro_qualification_order,
    plan_orders,
)
from blob.portfolio import Portfolio
from blob.universe import BASE

CFG = Config(cmc_api_key="test")


def make_portfolio(holdings):
    return Portfolio(holdings=dict(holdings), peak_value=sum(holdings.values()))


def test_plan_orders_sells_before_buys():
    pf = make_portfolio({BASE: 0.0, "LINK": 15.0})
    prices = {"LINK": 1.0, "ETH": 1.0}
    orders = plan_orders(pf, prices, {"ETH": 1.0, BASE: 0.0}, CFG)
    assert [o.side for o in orders] == ["sell", "buy"]
    assert orders[0].symbol == "LINK"
    assert orders[1].symbol == "ETH"


def test_plan_orders_hysteresis_ignores_small_deltas():
    pf = make_portfolio({BASE: 1.0, "ETH": 14.0})
    prices = {"ETH": 1.0}
    # Target 0.95 ETH vs current ~0.93: delta below threshold -> no order.
    orders = plan_orders(pf, prices, {"ETH": 0.95, BASE: 0.05}, CFG)
    assert orders == []


def test_paper_buy_applies_cost():
    pf = make_portfolio({BASE: 15.0})
    PaperExecutor(CFG).execute(Order("buy", "ETH", 10.0), {"ETH": 2.0}, pf)
    assert pf.holdings[BASE] == 5.0
    assert abs(pf.holdings["ETH"] - (10.0 / 2.0) * (1 - CFG.cost_per_side)) < 1e-9


def test_paper_sell_applies_cost():
    pf = make_portfolio({BASE: 0.0, "ETH": 5.0})
    PaperExecutor(CFG).execute(Order("sell", "ETH", 10.0), {"ETH": 2.0}, pf)
    assert abs(pf.holdings[BASE] - 10.0 * (1 - CFG.cost_per_side)) < 1e-9


def test_paper_buy_cannot_overspend_base():
    pf = make_portfolio({BASE: 3.0})
    PaperExecutor(CFG).execute(Order("buy", "ETH", 10.0), {"ETH": 1.0}, pf)
    assert pf.holdings[BASE] == 0.0
    assert pf.holdings["ETH"] <= 3.0


def test_qualification_trade_buys_when_base_available():
    pf = make_portfolio({BASE: 15.0})
    order = micro_qualification_order(CFG, pf, {})
    assert order == Order("buy", "ETH", 1.1)  # 10% buffer above the floor


def test_qualification_trade_sells_when_fully_deployed():
    pf = make_portfolio({BASE: 0.0, "ETH": 2.0, "LINK": 10.0})
    order = micro_qualification_order(CFG, pf, {"ETH": 1.0, "LINK": 1.0})
    assert order == Order("sell", "LINK", 1.1)


def test_qualification_trade_none_on_dust_portfolio():
    pf = make_portfolio({BASE: 0.1})
    assert micro_qualification_order(CFG, pf, {}) is None


def test_qualification_trade_requires_reserve_margin():
    # Base just at the trade size but under the 1.5x reserve -> sell side wins.
    pf = make_portfolio({BASE: 1.2, "ETH": 10.0})
    order = micro_qualification_order(CFG, pf, {"ETH": 1.0})
    assert order == Order("sell", "ETH", 1.1)


def test_stale_price_fallback_avoids_fake_crash():
    pf = make_portfolio({BASE: 5.0, "ETH": 10.0})
    prices = pf.update_prices({"ETH": 1.0})
    assert pf.value(prices) == 15.0
    # Next cycle the feed misses ETH: last known price must be used.
    prices = pf.update_prices({})
    assert pf.value(prices) == 15.0


def test_sell_clamped_to_held_balance():
    # Live-verified failure mode: selling $2.00 while holding $1.99 reverts.
    order = Order("sell", "ETH", 2.0)
    usd = clamp_order_usd(order, {"ETH": 1644.0}, {"ETH": 0.00121})
    assert usd <= 0.00121 * 1644.0 * 0.98
    assert usd < 2.0


def test_buy_clamped_to_base_balance():
    order = Order("buy", "ETH", 10.0)
    assert clamp_order_usd(order, {"ETH": 1.0}, {BASE: 5.0}) == 5.0 * 0.98


def test_clamp_leaves_small_orders_alone():
    order = Order("sell", "ETH", 1.1)
    assert clamp_order_usd(order, {"ETH": 1.0}, {"ETH": 100.0}) == 1.1


def test_round_trip_loses_about_double_cost():
    pf = make_portfolio({BASE: 15.0})
    ex = PaperExecutor(CFG)
    ex.execute(Order("buy", "ETH", 15.0), {"ETH": 1.0}, pf)
    ex.execute(Order("sell", "ETH", 100.0), {"ETH": 1.0}, pf)  # sell everything
    final = pf.holdings[BASE]
    expected = 15.0 * (1 - CFG.cost_per_side) ** 2
    assert abs(final - expected) < 1e-9
