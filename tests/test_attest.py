from blob.attest import attest_payload, decision_digest


def test_digest_is_deterministic_and_order_independent():
    a = {"ts": "2026-06-22T00:00:00+00:00", "exposure": 0.65,
         "weights": {"ETH": 0.32, "USDT": 0.35, "CAKE": 0.33},
         "fear_greed": 40, "reasons": ["regime: mixed (0.65)"]}
    b = {"reasons": ["regime: mixed (0.65)"], "fear_greed": 40,
         "weights": {"CAKE": 0.33, "USDT": 0.35, "ETH": 0.32},
         "exposure": 0.65, "ts": "2026-06-22T00:00:00+00:00"}
    # Same content, different key/dict order -> identical digest (canonical JSON).
    assert decision_digest(a) == decision_digest(b)


def test_digest_changes_with_content():
    base = {"ts": "t", "exposure": 0.5, "weights": {"ETH": 0.5, "USDT": 0.5},
            "fear_greed": 30, "reasons": ["x"]}
    other = {**base, "exposure": 0.65}
    assert decision_digest(base) != decision_digest(other)


def test_digest_is_0x_prefixed_32_bytes():
    d = decision_digest({"a": 1})
    assert d.startswith("0x") and len(d) == 66  # 0x + 64 hex chars


def test_attest_payload_extracts_recomputable_subset():
    summary = {"ts": "t", "mode": "live", "value_usd": 14.9, "drawdown": 0.01,
               "exposure": 0.65, "weights": {"ETH": 0.65, "USDT": 0.35},
               "fear_greed": 40, "reasons": ["r"], "orders": [], "holdings": {}}
    p = attest_payload(summary)
    assert set(p) == {"ts", "exposure", "weights", "fear_greed", "reasons"}
    # Recomputable from the published audit entry (same fields).
    assert decision_digest(p) == decision_digest(attest_payload(summary))
