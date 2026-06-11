from datetime import datetime, timezone

from blob.scheduler import seconds_until_next_hour
from blob.x402 import MAX_PAYMENT_ATOMIC, USDT_BSC, build_request_cmd


def test_x402_cmd_pays_capped_usdt_on_bsc():
    cmd = build_request_cmd(["BTC", "ETH"])
    assert cmd[:3] == ["twak", "x402", "request"]
    assert "symbol=BTC,ETH" in cmd[3]
    assert "--prefer-network" in cmd and cmd[cmd.index("--prefer-network") + 1] == "bsc"
    assert "--prefer-asset" in cmd and cmd[cmd.index("--prefer-asset") + 1] == USDT_BSC
    assert "--max-payment" in cmd and cmd[cmd.index("--max-payment") + 1] == MAX_PAYMENT_ATOMIC
    assert "--yes" in cmd
    # The wallet password must never appear on the command line.
    assert "--password" not in cmd


def test_x402_parse_filters_dead_ticker_squatters():
    from blob.x402 import parse_quotes
    payload = {
        "data": [
            {"symbol": "ETH", "is_active": 0, "id": 2,
             "quote": [{"symbol": "USD", "price": 0.001, "market_cap": 1}]},
            {"symbol": "ETH", "is_active": 1, "id": 1027,
             "quote": [{"symbol": "USD", "price": 1643.85, "market_cap": 2e11,
                        "percent_change_24h": -0.28, "percent_change_7d": -7.1,
                        "last_updated": "2026-06-11T16:37:04.000Z"}]},
            {"symbol": "ETH", "is_active": 1, "id": 9999,
             "quote": [{"symbol": "USD", "price": 5.0, "market_cap": 1e6}]},
        ],
        "status": {"credit_count": 1},
    }
    out = parse_quotes(payload, "ETH")
    assert out["cmc_id"] == 1027 and out["price"] == 1643.85 and out["credit_count"] == 1


def test_x402_parse_returns_none_when_no_active_match():
    from blob.x402 import parse_quotes
    assert parse_quotes({"data": []}, "ETH") is None


def test_seconds_until_next_hour():
    now = datetime(2026, 6, 22, 10, 59, 0, tzinfo=timezone.utc)
    assert abs(seconds_until_next_hour(now) - 60.0) < 1e-6
    now = datetime(2026, 6, 22, 10, 0, 0, tzinfo=timezone.utc)
    assert abs(seconds_until_next_hour(now) - 3600.0) < 1e-6
