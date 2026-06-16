"""BNB AI Agent SDK demo — standalone, fully isolated from the live trading agent.

Submission for the "Best Use of BNB AI Agent SDK" special prize. This module is
NOT imported by the Blob trading agent: the SDK requires a raw private key, which
is fundamentally incompatible with TWAK's no-export self-custody model. That
incompatibility is what GUARANTEES isolation — this runs on its own throwaway
wallet on BSC testnet (gas-free via the MegaFuel paymaster), touching nothing in
~/.twak, the trading wallet, or the live agent's state.

What it shows: an autonomous trading agent registering a first-class on-chain
identity (ERC-8004) through the BNB SDK, with structured metadata describing the
strategy, and reading it back from the chain. The agent's live decisions are
already attested on its TWAK-minted mainnet identity (see main README); this
demo exercises the BNB SDK's own identity stack on testnet.

Run:
    python -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python demo.py
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from bnbagent import AgentEndpoint, ERC8004Agent, EVMWalletProvider

WALLET_DIR = Path(__file__).resolve().parent / ".wallet"  # contained, gitignored


def main() -> None:
    # Throwaway testnet wallet — generated here, never reused for real funds,
    # never the TWAK trading wallet. Password from env or a random ephemeral one.
    password = os.environ.get("BNB_DEMO_PASSWORD") or secrets.token_hex(16)
    private_key = os.environ.get("BNB_DEMO_PRIVATE_KEY")  # None -> SDK generates one

    wallet = EVMWalletProvider(
        password=password,
        private_key=private_key,
        persist=True,
        wallets_dir=str(WALLET_DIR),
    )
    print(f"demo wallet (testnet, throwaway): {wallet.address}")

    agent = ERC8004Agent(wallet_provider=wallet, network="bsc-testnet")

    agent_uri = agent.generate_agent_uri(
        name="Blob",
        description=(
            "Risk-first autonomous spot-trading agent on BNB Chain. Reads CMC "
            "market data, decides with a deterministic regime+momentum core under "
            "hard drawdown guardrails, executes self-custodially via TWAK."
        ),
        endpoints=[
            AgentEndpoint(
                name="repo",
                endpoint="https://github.com/RedGnad/Blob",
                version="0.1.0",
                capabilities=["spot-trading", "risk-management", "self-custody"],
            ),
        ],
    )
    print(f"agent URI: {agent_uri[:80]}...")

    result = agent.register_agent(
        agent_uri=agent_uri,
        metadata=[
            {"key": "strategy", "value": "regime+momentum, drawdown-laddered, cost-aware"},
            {"key": "execution", "value": "twak-self-custody-bsc"},
        ],
    )
    agent_id = result.get("agentId")
    tx = result.get("transactionHash")
    gas_price = (result.get("receipt") or {}).get("effectiveGasPrice")
    print(f"registered ERC-8004 identity via BNB SDK: agentId={agent_id}")
    print(f"  tx: {tx}")
    print(f"  explorer: https://testnet.bscscan.com/tx/{tx}")
    print(f"  gas price: {gas_price} (0 == gas-free via MegaFuel paymaster)")

    if agent_id is not None:
        info = agent.get_agent_info(int(agent_id))
        print(f"read-back from chain: owner={info.get('owner')} uri_len={len(info.get('agentURI',''))}")


if __name__ == "__main__":
    main()
