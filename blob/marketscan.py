"""Attested market analysis from the CoinMarketCap AI Agent Hub (MCP).

This is the agent's deep-Hub capability, kept ISOLATED from the frozen trading
core: it genuinely consumes several rich MCP tools (derivatives & funding,
global metrics, BTC technicals, trending narratives, macro events) and
synthesises a structured market read, then commits its digest on-chain (ERC-8004
metadata) so the analysis is recompute-verifiable — same trustless guarantee as
the trading decisions.

It informs reasoning/narrative only. It NEVER feeds the risk-critical, backtested
position sizing (that stays deterministic and frozen). No alpha claim — it's a
transparent reading of real Hub data.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from .attest import attest_onchain, decision_digest
from .config import PROJECT_ROOT, Config
from .mcp_client import CmcMcpClient

log = logging.getLogger(__name__)

BTC_ID = "1"


def _safe(client: CmcMcpClient, tool: str, args: dict | None = None):
    try:
        return client.call_tool(tool, args or {})
    except Exception as exc:  # noqa: BLE001 — isolated, must never crash the agent
        log.warning("MCP tool %s failed: %s", tool, str(exc)[:160])
        return None


def _rows(payload, key):
    """Extract a list of dict-rows from CMC's {headers, rows} table shape."""
    block = (payload or {}).get(key, {}) if isinstance(payload, dict) else {}
    headers, rows = block.get("headers"), block.get("rows")
    if not headers or not rows:
        return []
    return [dict(zip(headers, r)) for r in rows]


def scan(cfg: Config) -> dict:
    """Consume the rich MCP tools and synthesise a structured market read."""
    client = CmcMcpClient(cfg.cmc_api_key)
    consumed: list[str] = []
    try:
        deriv = _safe(client, "get_global_crypto_derivatives_metrics")
        tech = _safe(client, "get_crypto_technical_analysis", {"id": BTC_ID})
        narr = _safe(client, "trending_crypto_narratives")
        macro = _safe(client, "get_upcoming_macro_events")
        glob = _safe(client, "get_global_metrics_latest")
    finally:
        client.close()

    analysis: dict = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "CoinMarketCap AI Agent Hub (MCP)",
        "mcp_tools_consumed": consumed,
    }

    if deriv:
        consumed.append("get_global_crypto_derivatives_metrics")
        oi = deriv.get("totalOpenInterest", {})
        analysis["derivatives"] = {
            "open_interest": oi.get("current"),
            "oi_30d": oi.get("percentage_change_30d"),
            "oi_7d": oi.get("percentage_change_7d"),
        }
    if tech:
        consumed.append("get_crypto_technical_analysis")
        ma = tech.get("moving_averages", {})
        analysis["btc_technical"] = {
            "sma_7d": ma.get("simple_moving_average_7_day"),
            "sma_30d": ma.get("simple_moving_average_30_day"),
            "sma_200d": ma.get("simple_moving_average_200_day"),
        }
    if narr:
        consumed.append("trending_crypto_narratives")
        top = _rows(narr, "categoryList")[:3]
        analysis["top_narratives"] = [
            {"name": r.get("categoryName"), "mc_7d": r.get("marketCapChangePercentage7d")}
            for r in top
        ]
    if macro:
        consumed.append("get_upcoming_macro_events")
        events = _rows(macro, "upcomingEventNews")
        if events:
            analysis["next_macro_event"] = {
                "title": events[0].get("title"), "date": events[0].get("eventDate"),
            }
    if glob:
        consumed.append("get_global_metrics_latest")
        analysis["global_snapshot"] = str(glob.get("market_size", {}).get(
            "total_crypto_market_cap", glob.get("last_updated")))[:120]

    analysis["synthesis"] = _synthesise(analysis)
    return analysis


def _synthesise(a: dict) -> str:
    """Deterministic one-line read of the fetched data (no LLM, no alpha claim)."""
    parts = []
    tech = a.get("btc_technical") or {}
    s7, s200 = _num(tech.get("sma_7d")), _num(tech.get("sma_200d"))
    if s7 and s200:
        parts.append("BTC below its 200-day trend" if s7 < s200 else "BTC above its 200-day trend")
    oi30 = a.get("derivatives", {}).get("oi_30d")
    if oi30:
        parts.append(f"derivatives {'deleveraging' if oi30.strip().startswith('-') else 'leveraging up'} (OI 30d {oi30})")
    nar = a.get("top_narratives") or []
    if nar and nar[0].get("name"):
        parts.append(f"hot narrative: {nar[0]['name']}")
    ev = a.get("next_macro_event")
    if ev and ev.get("title"):
        parts.append(f"watch: {ev['title'][:50]}")
    return "; ".join(parts) or "insufficient data"


def _num(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return None


def run_and_attest(cfg: Config) -> dict:
    """Scan, attest the analysis digest on-chain, log it."""
    analysis = scan(cfg)
    digest = decision_digest(analysis)
    out = {"analysis": analysis, "digest": digest, "tx": None}
    if cfg.attest_enabled:
        key = f"scan-{datetime.now(timezone.utc).date().isoformat()}"
        out["tx"] = attest_onchain(cfg.erc8004_agent_id, key, digest)

    path = PROJECT_ROOT / "logs" / "marketscan.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(out) + "\n")
    return out
