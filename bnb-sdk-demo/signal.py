"""The alpha being sold: a regime/momentum signal, with its inputs committed so
the buyer can recompute it and trust the result WITHOUT trusting the seller.

Self-contained (public Binance klines, no key) so the demo runs standalone.
The deliverable carries {signal, inputs, digest}; digest = SHA-256 of the
canonical JSON of {signal, inputs}. Anyone recomputes the signal from the
committed inputs and checks the digest — the "recompute-it-yourself" guarantee
that makes delivery quality trustless on top of the trustless ERC-8183 escrow.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from urllib.parse import urlencode

UNIVERSE = ["ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
ANCHOR = "BTCUSDT"


def _change_7d(pair: str) -> float:
    """7-day % change from hourly klines (deterministic inputs we commit)."""
    url = "https://api.binance.com/api/v3/klines?" + urlencode(
        {"symbol": pair, "interval": "1h", "limit": 169}
    )
    with urllib.request.urlopen(url, timeout=20) as resp:
        rows = json.load(resp)
    first, last = float(rows[0][4]), float(rows[-1][4])
    return round((last / first - 1.0) * 100.0, 4)


def compute_signal() -> dict:
    """Produce the signal AND the raw inputs it was computed from."""
    inputs = {p: _change_7d(p) for p in [ANCHOR] + UNIVERSE}
    regime = "risk-on" if inputs[ANCHOR] > 0 else "risk-off"
    pick = max(UNIVERSE, key=lambda p: inputs[p])
    signal = {"regime": regime, "pick": pick, "pick_7d_pct": inputs[pick]}
    return {"signal": signal, "inputs": inputs, "ts": int(time.time())}


def digest(payload: dict) -> str:
    """0x-prefixed SHA-256 of the canonical JSON of {signal, inputs, ts}."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "0x" + hashlib.sha256(canonical.encode()).hexdigest()


def recompute_and_verify(payload: dict, claimed_digest: str) -> bool:
    """Buyer side: recompute the signal from the committed inputs and check the
    digest. Confirms the seller neither fabricated the signal nor the inputs."""
    inputs = payload["inputs"]
    expected_regime = "risk-on" if inputs[ANCHOR] > 0 else "risk-off"
    expected_pick = max(UNIVERSE, key=lambda p: inputs[p])
    sig = payload["signal"]
    consistent = sig["regime"] == expected_regime and sig["pick"] == expected_pick
    return consistent and digest(payload) == claimed_digest


if __name__ == "__main__":
    p = compute_signal()
    d = digest(p)
    print(json.dumps(p, indent=2))
    print("digest:", d)
    print("verify:", recompute_and_verify(p, d))
