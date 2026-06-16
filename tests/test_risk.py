from blob import risk
from blob.config import Config
from blob.strategy import Decision
from blob.universe import BASE

# Pin drawdown thresholds so these logic tests don't track production defaults.
CFG = Config(cmc_api_key="test", dd_half=0.10, dd_kill=0.18)


def test_exposure_ladder():
    assert risk.exposure_cap(0.05, CFG) == 1.0
    assert risk.exposure_cap(0.10, CFG) == 0.5
    assert risk.exposure_cap(0.18, CFG) == 0.0
    assert risk.exposure_cap(0.50, CFG) == 0.0


def test_apply_scales_exposure_at_half_ladder():
    decision = Decision(exposure=1.0, weights={"ETH": 0.5, "LINK": 0.5, BASE: 0.0})
    out = risk.apply(decision, drawdown=0.12, cfg=CFG)
    assert abs(out.exposure - 0.5) < 1e-9
    assert abs(out.weights["ETH"] - 0.25) < 1e-9
    assert abs(out.weights[BASE] - 0.5) < 1e-9


def test_apply_kill_switch_goes_full_base():
    decision = Decision(exposure=1.0, weights={"ETH": 1.0, BASE: 0.0})
    out = risk.apply(decision, drawdown=0.20, cfg=CFG)
    assert out.exposure == 0.0
    assert out.weights[BASE] == 1.0


def test_apply_drops_non_allowlist_assets():
    decision = Decision(exposure=0.5, weights={"SCAMCOIN": 0.5, BASE: 0.5})
    out = risk.apply(decision, drawdown=0.0, cfg=CFG)
    assert "SCAMCOIN" not in out.weights
    assert out.weights[BASE] == 1.0


def test_weights_always_sum_to_one():
    decision = Decision(exposure=1.0, weights={"ETH": 0.7, "LINK": 0.3, BASE: 0.0})
    for dd in (0.0, 0.11, 0.25):
        out = risk.apply(decision, drawdown=dd, cfg=CFG)
        assert abs(sum(out.weights.values()) - 1.0) < 1e-9
