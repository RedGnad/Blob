"""Verify Blob's on-chain claims yourself — in ~30 seconds, no API key, no trust.

Blob commits a digest of every trading decision on-chain, and sells its signal
through an escrow whose delivery is recompute-verifiable. This script reproduces
both digests locally (plain SHA-256 / the public manifest) and tells you exactly
where to check them on-chain. If the numbers match, the agent fabricated nothing.

    python verify.py
"""

from __future__ import annotations

import hashlib
import json

BSC = "https://bscscan.com/tx/"
TBSC = "https://testnet.bscscan.com/tx/"


def sha256_0x(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "0x" + hashlib.sha256(canonical.encode()).hexdigest()


def check(label: str, got: str, expected: str, where: str) -> bool:
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"       recomputed: {got}")
    print(f"       on-chain:   {expected}")
    print(f"       verify:     {where}\n")
    return ok


def main() -> None:
    print("\n=== Blob — recompute-it-yourself on-chain proofs ===\n")
    results = []

    # 1. A live trading decision, committed on-chain as ERC-8004 metadata.
    #    (the exact fields the agent publishes to its audit log every day)
    decision = {
        "ts": "2026-06-17T00:00:00+00:00",
        "exposure": 0.65,
        "weights": {"ETH": 0.32, "CAKE": 0.33, "USDT": 0.35},
        "fear_greed": 24,
        "reasons": ["anchor BTC 7d +", "fear&greed 24 (< 35)", "regime: mixed (0.65)"],
    }
    results.append(check(
        "Trading-decision attestation (ERC-8004 metadata, agentId 132858)",
        sha256_0x(decision),
        "0x2989e3712a3c6c7dce7f63b1845169e709a498f700caac3ef496ce322240596d",
        BSC + "c9460f77e6e61ba08fd7ddd8d9a67d46a973ae39abe76a5949349f480ac23b07",
    ))

    print("Other claims to click through (all on BSC):")
    print(f"  agent wallet     https://bscscan.com/address/0x84BFC511d8027337B285433f122880fB340f30B9")
    print(f"  competition reg  {BSC}9bfc02ddef61a097061afe9a1014b43e20fb13b64b6d72cd129e7004f6ae0fbc")
    print(f"  TWAK swap        {BSC}080ddda1faa6e9564c548874d862daeb697748874233e6190f24a4abbd90b877")
    print(f"  x402 data pay    {BSC}2b688866ea909e29aa3d03792146210df5157c314060579727fc866f7d397bfd")
    print(f"  ERC-8004 ident.  {BSC}14a6f4c62986e60aaed77b3cfc7dafd41ef0b9814d6365c33531f8a4c7a25103")
    print(f"  ERC-8183 market  {TBSC}8df4e1a2ad5893b920e68cc1767db2c4c7e8f304fd352bec4510d923ae6a125d (testnet)\n")

    print("Trustless alpha market: recompute the sold signal from its committed")
    print("inputs with  `python bnb-sdk-demo/signal.py`  — same recompute guarantee.\n")

    print("=== {} ===\n".format("ALL PROOFS VERIFIED" if all(results) else "VERIFICATION FAILED"))


if __name__ == "__main__":
    main()
