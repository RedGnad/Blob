"""Use the CoinMarketCap AI Agent Hub *Skills library*, not just raw MCP.

CMC publishes its Skills as open-source workflow definitions (SKILL.md) in
github.com/coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap. A Skill
declares an intent and the exact MCP tools its workflow runs. `find_skill`
locates the official Skill for an intent and loads its definition from the CMC
repo; `execute_skill` runs the MCP tools that Skill declares. So our market
analysis is grounded in an *official CMC Skill*, executed faithfully — the
find_skill -> execute_skill pattern, over CMC's own catalog.
"""

from __future__ import annotations

import logging
import re

import httpx

from .mcp_client import CmcMcpClient

log = logging.getLogger(__name__)

SKILLS_RAW = (
    "https://raw.githubusercontent.com/coinmarketcap-official/"
    "skills-for-ai-agents-by-CoinMarketCap/main/skills"
)

# Intent -> official CMC Skill slug (matches each Skill's documented triggers).
_INTENT_TO_SKILL = {
    "market report": "market-report",
    "market overview": "market-report",
    "market sentiment": "market-report",
    "fear and greed": "market-report",
    "research": "crypto-research",
    "due diligence": "crypto-research",
}

# Default arguments for the tools a Skill may declare (BTC=1, ETH=1027).
_DEFAULT_ARGS = {
    "get_crypto_quotes_latest": {"id": "1,1027"},
    "get_crypto_technical_analysis": {"id": "1"},
    "get_crypto_latest_news": {"id": "1"},
    "get_crypto_metrics": {"id": "1"},
    "get_crypto_info": {"id": "1"},
    "search_cryptos": {"query": "bitcoin"},
    "search_crypto_info": {"prompt": "market overview", "id": "1"},
}

# Fallback tool set if the SKILL.md can't be fetched (keeps the agent resilient).
_FALLBACK_TOOLS = {
    "market-report": [
        "get_global_metrics_latest", "get_global_crypto_derivatives_metrics",
        "trending_crypto_narratives", "get_upcoming_macro_events",
        "get_crypto_marketcap_technical_analysis", "get_crypto_quotes_latest",
    ],
}


def find_skill(intent: str) -> dict | None:
    """Locate the official CMC Skill for an intent and load its definition."""
    slug = next((s for kw, s in _INTENT_TO_SKILL.items() if kw in intent.lower()), None)
    if not slug:
        return None
    url = f"{SKILLS_RAW}/{slug}/SKILL.md"
    md = ""
    try:
        resp = httpx.get(url, timeout=20.0)
        resp.raise_for_status()
        md = resp.text
    except httpx.HTTPError as exc:
        log.warning("could not load Skill %s (%s), using declared fallback", slug, exc)
    tools = sorted(set(re.findall(r"mcp__cmc-mcp__(\w+)", md))) or _FALLBACK_TOOLS.get(slug, [])
    return {"name": slug, "source": url, "tools": tools, "loaded_from_repo": bool(md)}


def execute_skill(skill: dict, client: CmcMcpClient) -> dict:
    """Run the MCP tools the Skill declares; return {tool_name: payload}."""
    out: dict = {}
    for tool in skill["tools"]:
        try:
            out[tool] = client.call_tool(tool, _DEFAULT_ARGS.get(tool, {}))
        except Exception as exc:  # noqa: BLE001 — isolated, resilient
            log.warning("skill tool %s failed: %s", tool, str(exc)[:120])
            out[tool] = None
    return out
