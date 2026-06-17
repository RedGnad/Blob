"""The deep Agent Hub analysis layer is isolated from the trading core; these
test its deterministic, network-free parts (table extraction + synthesis)."""

from blob.marketscan import _num, _rows, _synthesise


def test_rows_extracts_cmc_table_shape():
    payload = {"categoryList": {
        "headers": ["categoryName", "marketCapChangePercentage7d"],
        "rows": [["Layer 1", "+5.1%"], ["Memes", "-2.0%"]],
    }}
    rows = _rows(payload, "categoryList")
    assert rows[0] == {"categoryName": "Layer 1", "marketCapChangePercentage7d": "+5.1%"}
    assert _rows({}, "categoryList") == []


def test_num_parses_formatted_numbers():
    assert _num("77,394.28") == 77394.28
    assert _num(None) is None
    assert _num("n/a") is None


def test_synthesis_reads_the_real_data():
    a = {
        "btc_technical": {"sma_7d": "64,367", "sma_200d": "77,394"},
        "derivatives": {"oi_30d": "-20.8%"},
        "top_narratives": [{"name": "Binance Ecosystem"}],
        "next_macro_event": {"title": "Federal Reserve policy decision"},
    }
    s = _synthesise(a)
    assert "below its 200-day trend" in s          # 64k < 77k
    assert "deleveraging" in s                      # OI negative
    assert "Binance Ecosystem" in s
    assert "Federal Reserve" in s


def test_synthesis_flags_leverage_build_and_uptrend():
    a = {"btc_technical": {"sma_7d": "80,000", "sma_200d": "77,394"},
         "derivatives": {"oi_30d": "+12.0%"}}
    s = _synthesise(a)
    assert "above its 200-day trend" in s
    assert "leveraging up" in s


def test_synthesis_degrades_gracefully():
    assert _synthesise({}) == "insufficient data"
