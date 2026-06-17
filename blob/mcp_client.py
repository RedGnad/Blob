"""Minimal client for the CoinMarketCap AI Agent Hub MCP server.

The Hub's flagship surface: a single MCP endpoint exposing rich tools (CEX +
derivatives, on-chain metrics, news, technical analysis, narratives, macro
events) far beyond the REST quotes the trading core uses. This client is used
ONLY by the isolated market-analysis layer (blob/marketscan.py) — never by the
trading decision path.
"""

from __future__ import annotations

import json
import logging

import httpx

log = logging.getLogger(__name__)

MCP_ENDPOINT = "https://mcp.coinmarketcap.com/mcp"


class McpError(RuntimeError):
    pass


class CmcMcpClient:
    def __init__(self, api_key: str, timeout: float = 30.0):
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "X-CMC-MCP-API-KEY": api_key,
            },
        )
        self._id = 0

    def call_tool(self, name: str, arguments: dict | None = None) -> dict | list:
        """Invoke an MCP tool and return its parsed JSON payload."""
        self._id += 1
        resp = self._client.post(MCP_ENDPOINT, json={
            "jsonrpc": "2.0", "id": self._id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        })
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            raise McpError(f"{name}: {body['error']}")
        result = body.get("result", {})
        if result.get("isError"):
            raise McpError(f"{name}: {result.get('content')}")
        # Tool payload is JSON-encoded text in result.content[0].text.
        text = result["content"][0]["text"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text  # some tools return plain text

    def close(self) -> None:
        self._client.close()
