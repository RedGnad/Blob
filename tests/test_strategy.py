from blob.config import Config
from blob.datafeed import Quote
from blob.strategy import momentum_score, regime_exposure, select_candidates, target_allocation
from blob.universe import BASE, REGIME_ANCHOR

# Pin regime params so these logic tests don't track production defaults.
CFG = Config(cmc_api_key="test", fg_risk_on=45, mixed_exposure=0.5)


def q(symbol, pct_24h=0.0, pct_7d=0.0, price=100.0):
    return Quote(symbol=symbol, price=price, pct_1h=0.0, pct_24h=pct_24h,
                 pct_7d=pct_7d, market_cap=1e9)


def test_regime_risk_on():
    quotes = {REGIME_ANCHOR: q(REGIME_ANCHOR, pct_7d=5.0)}
    exposure, _ = regime_exposure(quotes, fear_greed=60, cfg=CFG)
    assert exposure == 1.0


def test_regime_mixed_and_off():
    quotes_up = {REGIME_ANCHOR: q(REGIME_ANCHOR, pct_7d=5.0)}
    quotes_down = {REGIME_ANCHOR: q(REGIME_ANCHOR, pct_7d=-5.0)}
    assert regime_exposure(quotes_up, fear_greed=20, cfg=CFG)[0] == 0.5
    assert regime_exposure(quotes_down, fear_greed=60, cfg=CFG)[0] == 0.5
    assert regime_exposure(quotes_down, fear_greed=20, cfg=CFG)[0] == 0.0


def test_missing_anchor_is_not_risk_on():
    exposure, _ = regime_exposure({}, fear_greed=80, cfg=CFG)
    assert exposure == 0.5


def test_select_filters_below_momentum_floor():
    quotes = {"ETH": q("ETH", pct_24h=1.0, pct_7d=1.0),   # score 1.0 < 2.0
              "LINK": q("LINK", pct_24h=5.0, pct_7d=5.0)}  # score 5.0
    picks = select_candidates(quotes, CFG)
    assert [p.symbol for p in picks] == ["LINK"]


def test_select_top_k_ordering():
    quotes = {"ETH": q("ETH", pct_24h=10.0, pct_7d=10.0),
              "LINK": q("LINK", pct_24h=5.0, pct_7d=5.0),
              "DOGE": q("DOGE", pct_24h=8.0, pct_7d=8.0)}
    picks = select_candidates(quotes, CFG)
    assert len(picks) == CFG.top_k
    scores = [momentum_score(p) for p in picks]
    assert scores == sorted(scores, reverse=True)


def test_target_allocation_sums_to_one():
    quotes = {REGIME_ANCHOR: q(REGIME_ANCHOR, pct_7d=5.0),
              "ETH": q("ETH", pct_24h=10.0, pct_7d=10.0)}
    decision = target_allocation(quotes, fear_greed=60, cfg=CFG)
    assert abs(sum(decision.weights.values()) - 1.0) < 1e-9
    assert decision.weights[BASE] == 0.0
    assert decision.weights["ETH"] == 1.0


def test_cost_aware_entry_floor_blocks_expensive_tokens():
    # Post fee-waiver: PENDLE round-trip 2.11% -> entry floor 4.22%; ETH 0.15%
    # -> floor falls back to min_momentum_pct (2.0). Momentum 3% clears ETH's
    # floor but not PENDLE's.
    quotes = {"PENDLE": q("PENDLE", pct_24h=3.0, pct_7d=3.0),
              "ETH": q("ETH", pct_24h=3.0, pct_7d=3.0)}
    picks = select_candidates(quotes, CFG)
    assert [p.symbol for p in picks] == ["ETH"]


def test_held_asset_survives_with_lower_exit_floor():
    quotes = {"ETH": q("ETH", pct_24h=1.0, pct_7d=1.0)}  # score 1.0: below entry, above exit
    assert select_candidates(quotes, CFG) == []
    picks = select_candidates(quotes, CFG, held={"ETH"})
    assert [p.symbol for p in picks] == ["ETH"]


def test_held_asset_below_exit_floor_is_dropped():
    quotes = {"ETH": q("ETH", pct_24h=-2.0, pct_7d=-2.0)}  # score -2.0 < exit floor 0.0
    assert select_candidates(quotes, CFG, held={"ETH"}) == []


def test_no_candidates_means_all_base():
    quotes = {REGIME_ANCHOR: q(REGIME_ANCHOR, pct_7d=5.0),
              "ETH": q("ETH", pct_24h=0.1, pct_7d=0.1)}
    decision = target_allocation(quotes, fear_greed=60, cfg=CFG)
    assert decision.weights == {BASE: 1.0}
    assert decision.exposure == 0.0
