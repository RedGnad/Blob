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

## Proven run (BSC testnet, job #212)

Full buy → fund → deliver lifecycle, on-chain, with the recompute-verification passing:

| Step | tx |
|---|---|
| create_job (#212) | [`d267d1ff…`](https://testnet.bscscan.com/tx/d267d1ff65f52b9bb0d7fb52f211fe7b946214294f2c4bd73b49316299287b15) |
| register_job (bind OptimisticPolicy) | [`a8a7d8dc…`](https://testnet.bscscan.com/tx/a8a7d8dc20277dfb2f7bd1fd79ef02f160baf1e936fdab88e92e94ee17a95297) |
| fund (escrow, 1 U) | [`36d8fe61…`](https://testnet.bscscan.com/tx/36d8fe61faa94dfcc815d83f445c2e07f7f43deba276dee0c87d4fdd0383a1d5) |
| submit (deliverable `0xe7519b5f…`) | [`8df4e1a2…`](https://testnet.bscscan.com/tx/8df4e1a2ad5893b920e68cc1767db2c4c7e8f304fd352bec4510d923ae6a125d) |

```
verify  manifest_integrity=True  signal_recompute=True
```

`settle` is permissionless and completes the job to COMPLETED after the
OptimisticPolicy dispute window (1 day on testnet): `python market.py --settle`.

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
