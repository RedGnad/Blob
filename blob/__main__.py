import argparse
import json
import logging
import os

from .agent import run_once, status
from .config import PROJECT_ROOT, Config, load_dotenv


def doctor() -> None:
    """Diagnose configuration without ever printing secret values."""
    env_path = PROJECT_ROOT / ".env"
    print(f".env at {env_path}: {'found' if env_path.exists() else 'NOT FOUND'}")
    load_dotenv()
    for key in ("CMC_API_KEY", "TWAK_ACCESS_ID", "TWAK_HMAC_SECRET",
                "AGENT_WALLET_ADDRESS", "MODE", "EXECUTOR_FALLBACK"):
        print(f"  {key}: {'present' if os.environ.get(key, '').strip() else 'MISSING or empty'}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="blob", description="Blob trading agent")
    sub = parser.add_subparsers(dest="command", required=True)
    ro = sub.add_parser("run-once", help="one full cycle: data -> decision -> orders -> execution")
    ro.add_argument("--rebalance", action="store_true",
                    help="force a full strategy rebalance (debug/ops)")
    sub.add_parser("status", help="portfolio value, drawdown, holdings")
    sub.add_parser("loop", help="24/7 runner: hourly cycles, retries, desktop alerts")
    sub.add_parser("doctor", help="check config presence (never prints secret values)")
    bt = sub.add_parser("backtest", help="replay the decision core on history (keyless)")
    bt.add_argument("--days", type=int, default=90)
    bt.add_argument("--fast-lane", action="store_true")
    bt.add_argument("--compare", action="store_true",
                    help="run baseline AND fast-lane on the same data")
    costs = sub.add_parser("costs", help="measure real round-trip costs via twak quotes")
    costs.add_argument("--usd", type=float, default=5.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.command == "doctor":
        doctor()
        return

    if args.command == "costs":
        from .costs import measure_all
        print(json.dumps(measure_all(usd=args.usd), indent=2))
        return

    if args.command == "backtest":
        from .backtest import run_backtest, run_comparison
        cfg = Config(cmc_api_key="unused-offline", fast_lane=args.fast_lane)
        if args.compare:
            print(json.dumps(run_comparison(cfg, days=args.days), indent=2))
        else:
            print(json.dumps(run_backtest(cfg, days=args.days), indent=2))
        return

    cfg = Config.from_env()

    if args.command == "run-once":
        print(json.dumps(run_once(cfg, full_rebalance=True if args.rebalance else None), indent=2))
    elif args.command == "status":
        print(json.dumps(status(cfg), indent=2))
    elif args.command == "loop":
        from .scheduler import loop
        loop(cfg)


if __name__ == "__main__":
    main()
