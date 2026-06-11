"""Configuration loading. Secrets are read from .env / environment and must
never be printed or logged: secret fields are excluded from repr."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader: KEY=VALUE lines, '#' comments. Does not override
    variables already set in the environment."""
    path = path or PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.split("#")[0].strip()
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Config:
    cmc_api_key: str = field(repr=False)
    mode: str = "paper"  # paper | live
    executor_fallback: bool = False
    x402_enabled: bool = False  # pay-per-request data via TWAK x402 (needs funded wallet)
    twak_access_id: str = field(default="", repr=False)
    twak_hmac_secret: str = field(default="", repr=False)
    agent_wallet_address: str = ""

    # Strategy / risk parameters (see docs/redteam.md for rationale)
    paper_start_usdt: float = 15.0
    cost_per_side: float = 0.007        # ~1.4% round-trip measured on BSC via TWAK
    min_momentum_pct: float = 2.0       # entry: expected edge must clear the cost floor
    exit_momentum_pct: float = 0.0      # exit floor for already-held assets (anti-churn)
    retention_bonus_pct: float = 2.0    # challenger must beat a held asset by this margin
    top_k: int = 2
    rebalance_fraction: float = 0.20    # per-asset delta below this fraction of NAV is noise
    min_trade_usd: float = 1.0
    dd_half: float = 0.10               # halve exposure
    dd_kill: float = 0.18               # all to USDT (official DQ ~30%)
    fg_risk_on: int = 45                # Fear & Greed threshold for risk-on regime

    # Fast lane: in a strongly risk-on regime, concentrate on the single best
    # momentum asset instead of top_k (more upside in explosive weeks, the
    # drawdown ladder still bounds the damage). Off by default pending backtest.
    fast_lane: bool = False
    fast_anchor_7d_pct: float = 5.0
    fast_fg: int = 60

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        mode = os.environ.get("MODE", "paper").strip().lower()
        missing = []
        cmc_key = os.environ.get("CMC_API_KEY", "").strip()
        if not cmc_key:
            missing.append("CMC_API_KEY")
        twak_id = os.environ.get("TWAK_ACCESS_ID", "").strip()
        twak_secret = os.environ.get("TWAK_HMAC_SECRET", "").strip()
        wallet = os.environ.get("AGENT_WALLET_ADDRESS", "").strip()
        if mode == "live":
            if not twak_id:
                missing.append("TWAK_ACCESS_ID")
            if not twak_secret:
                missing.append("TWAK_HMAC_SECRET")
            if not wallet:
                missing.append("AGENT_WALLET_ADDRESS")
        if missing:
            raise SystemExit(
                f"Missing required environment variables for mode={mode}: "
                f"{', '.join(missing)} (fill them in .env, values are never logged)"
            )
        return cls(
            cmc_api_key=cmc_key,
            mode=mode,
            executor_fallback=os.environ.get("EXECUTOR_FALLBACK", "0").strip() == "1",
            x402_enabled=os.environ.get("X402_ENABLED", "0").strip() == "1",
            twak_access_id=twak_id,
            twak_hmac_secret=twak_secret,
            agent_wallet_address=wallet,
        )
