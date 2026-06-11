"""Risk engine: last gate before any order is planned. Applied OUTSIDE the
strategy (and outside any LLM), per docs/redteam.md R11/R12.

Drawdown ladder (official DQ ~30%, we keep a wide margin):
- dd >= dd_kill (18%): everything to BASE until the end of the window
- dd >= dd_half (10%): exposure capped at half
"""

from __future__ import annotations

from .config import Config
from .strategy import Decision
from .universe import ALLOWLIST, BASE


def exposure_cap(drawdown: float, cfg: Config) -> float:
    if drawdown >= cfg.dd_kill:
        return 0.0
    if drawdown >= cfg.dd_half:
        return 0.5
    return 1.0


def apply(decision: Decision, drawdown: float, cfg: Config) -> Decision:
    cap = exposure_cap(drawdown, cfg)
    reasons = list(decision.reasons) + [f"drawdown {drawdown:.1%} -> exposure cap {cap:.1f}"]

    risk_weights = {
        s: w for s, w in decision.weights.items()
        if s != BASE and s in ALLOWLIST and w > 0
    }
    dropped = [s for s in decision.weights if s != BASE and s not in ALLOWLIST]
    if dropped:
        reasons.append(f"dropped non-allowlist: {', '.join(dropped)}")

    current_exposure = sum(risk_weights.values())
    if current_exposure > cap:
        scale = cap / current_exposure if current_exposure > 0 else 0.0
        risk_weights = {s: w * scale for s, w in risk_weights.items()}
        reasons.append(f"exposure scaled {current_exposure:.2f} -> {cap:.2f}")

    final_exposure = sum(risk_weights.values())
    weights = {**risk_weights, BASE: 1.0 - final_exposure}
    return Decision(exposure=final_exposure, weights=weights, reasons=reasons)
