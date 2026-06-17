# Trustless agent-to-agent alpha market — Best Use of BNB AI Agent SDK

An inventive use of the [BNB AI Agent SDK](https://github.com/bnb-chain/bnbagent-sdk)'s
flagship primitive, **ERC-8183 agentic commerce**, submitted for the "Best Use of
BNB AI Agent SDK" special prize. Not the quickstart mint — a market that doesn't
exist without the SDK.

## The idea

**Blob sells its regime/momentum signal to another agent through an ERC-8183 job
escrow, and the delivery is a recompute-it-yourself attestation.** Two trustless
layers stack:

1. **ERC-8183 escrow → trustless payment.** The buyer funds an escrow; funds
   release only on delivery (silence past the dispute window approves; a dispute
   triggers a whitelisted-voter quorum).
2. **Recompute-able attestation → trustless quality.** The on-chain deliverable
   is `keccak256` of a manifest whose metadata carries the signal's *raw inputs*.
   The buyer recomputes the signal from those inputs and checks the seller
   fabricated nothing.

→ **agent-to-agent alpha the buyer can trust without trusting the seller.** The
escrow makes the payment trustless, the attestation makes the delivery trustless.

## Why it's isolated from the live agent

The SDK signs with a raw private key — fundamentally incompatible with TWAK's
no-export self-custody used by the live Blob agent. That incompatibility *is* the
isolation guarantee: this runs on its own throwaway testnet wallets, touching
nothing in the live agent. (The same attestation idea secures the live agent's
mainnet decisions — see the main README.)

## Status

- ✅ **Signal + recompute-verify layer** — works standalone on real data
  (`python signal.py`): generates a regime/momentum signal, commits a digest,
  recomputes and verifies. This is the trustless-quality half.
- ⏳ **On-chain ERC-8183 flow** (`market.py`) — complete, runs end-to-end once the
  buyer wallet is funded (see below). SDK escrow ops are MegaFuel-sponsored
  (gas-free); only the faucet claim + the ERC-20 approve need a little tBNB.

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
python signal.py        # standalone: signal + recompute-verify (no chain)

# to run the on-chain market, fund the BUYER wallet first:
#   1. tBNB (gas):  https://www.bnbchain.org/en/testnet-faucet
#   2. then:        python claim_u.py   # pulls 10 test "U" from the faucet
python market.py        # buy -> fund -> deliver -> settle + recompute-verify
```

Wallets are throwaway, generated on first run, gitignored.
