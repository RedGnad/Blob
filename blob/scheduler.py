"""24/7 runner for the live week (docs/redteam.md R3: a missed daily trade
means disqualification, so the loop must survive transient failures and
escalate loudly when it cannot).

Cadence: one cycle at startup, then aligned to the top of every hour
(strategy rebalance happens inside run_once at 00:00 UTC, every other cycle
is a risk-only check)."""

from __future__ import annotations

import logging
import platform
import subprocess
import time
from datetime import datetime, timezone

from .agent import run_once
from .config import Config

log = logging.getLogger(__name__)

RETRIES = 3
RETRY_DELAY_S = 180


def notify(message: str) -> None:
    """Best-effort desktop notification (macOS); always logged."""
    log.error("ALERT: %s", message)
    if platform.system() == "Darwin":
        script = f'display notification {json_escape(message)} with title "Blob agent" sound name "Basso"'
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
        except (subprocess.SubprocessError, OSError):
            pass


def json_escape(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def seconds_until_next_hour(now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    return 3600.0 - (now.minute * 60 + now.second + now.microsecond / 1e6)


def run_cycle_with_retries(cfg: Config) -> bool:
    for attempt in range(1, RETRIES + 1):
        try:
            summary = run_once(cfg)
            log.info(
                "cycle ok: value=%.2f dd=%.1f%% orders=%d",
                summary["value_usd"], summary["drawdown"] * 100, summary["orders_executed"],
            )
            return True
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            log.exception("cycle attempt %d/%d failed: %s", attempt, RETRIES, exc)
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY_S)
    notify(f"cycle failed after {RETRIES} attempts ({datetime.now(timezone.utc):%H:%M} UTC) — check logs")
    return False


def loop(cfg: Config) -> None:
    log.info("starting loop, mode=%s", cfg.mode)
    run_cycle_with_retries(cfg)
    while True:
        time.sleep(seconds_until_next_hour())
        run_cycle_with_retries(cfg)
