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


def test_seconds_until_next_hour():
    now = datetime(2026, 6, 22, 10, 59, 0, tzinfo=timezone.utc)
    assert abs(seconds_until_next_hour(now) - 60.0) < 1e-6
    now = datetime(2026, 6, 22, 10, 0, 0, tzinfo=timezone.utc)
    assert abs(seconds_until_next_hour(now) - 3600.0) < 1e-6
