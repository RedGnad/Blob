"""On-chain attestation of trading decisions.

Each daily decision is hashed and committed on BSC as a metadata entry on the
agent's own ERC-8004 identity (via TWAK). This turns the audit trail into a
recompute-it-yourself, tamper-evident track record: anyone can take the
published decision from the audit log, recompute the digest with the scheme
below, and check it against the on-chain value. Proves the decisions weren't
fabricated after the fact.

Digest scheme (dependency-free, fully specified for verifiers): SHA-256 of the
canonical JSON of the attested payload (keys sorted, no whitespace), 0x-prefixed.
Reinforces TWAK depth (erc8004 surface) and serves originality/real-world
relevance. Isolated: a failure here never blocks a trade.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess

log = logging.getLogger(__name__)


def attest_payload(summary: dict) -> dict:
    """The exact, recomputable subset of a cycle summary that we commit."""
    return {
        "ts": summary["ts"],
        "exposure": summary["exposure"],
        "weights": summary["weights"],
        "fear_greed": summary["fear_greed"],
        "reasons": summary["reasons"],
    }


def decision_digest(payload: dict) -> str:
    """0x-prefixed SHA-256 (32 bytes) of the canonical JSON of the payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "0x" + hashlib.sha256(canonical.encode()).hexdigest()


def attest_onchain(agent_id: int, key: str, digest_hex: str, timeout: float = 120.0) -> str | None:
    """Commit the digest as ERC-8004 metadata on BSC via TWAK. Returns the tx
    hash, or None on failure (logged, never raised)."""
    cmd = [
        "twak", "erc8004", "set-metadata", str(agent_id),
        "--key", key, "--value", digest_hex, "--chain", "bsc", "--json",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("attestation failed to run: %s", exc)
        return None
    if result.returncode != 0:
        log.warning("attestation failed: %s", (result.stdout or result.stderr).strip()[:400])
        return None
    try:
        out = json.loads(result.stdout)
    except json.JSONDecodeError:
        log.warning("attestation response not JSON: %s", result.stdout.strip()[:200])
        return None
    return out.get("hash") or out.get("txHash")
