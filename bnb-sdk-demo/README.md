# BNB AI Agent SDK demo — Best Use of BNB AI Agent SDK

Standalone integration of the [BNB AI Agent SDK](https://github.com/bnb-chain/bnbagent-sdk)
(`bnbagent`), submitted for the "Best Use of BNB AI Agent SDK" special prize.

**Why it's a separate folder, not part of the trading agent:** the SDK signs with a
raw private key, which is fundamentally incompatible with TWAK's no-export
self-custody model used by the live Blob agent. That incompatibility is exactly
what guarantees isolation — this demo runs on its own throwaway wallet on BSC
testnet, gas-free via the MegaFuel paymaster, and touches nothing in the live
agent (no shared wallet, key store, state, or code).

## What it does

Registers Blob's trading agent as a first-class on-chain identity through the SDK:
generates an ERC-8004 agent URI (name, description, capabilities), mints the
identity, attaches structured strategy metadata, and reads it back from the chain.

## Proven run (BSC testnet)

```
demo wallet (testnet, throwaway): 0xf8d7Ba5B512d73369E6a4F18e1A11a8CF5370f72
registered ERC-8004 identity via BNB SDK: agentId=1417
  tx: 0x1f0a67af7cf0735e409dd2a0b273a0397b1aaccef1627e107126c8e2056f8b17
  gas price: 0 (gas-free via MegaFuel paymaster)
```

[View on testnet BscScan](https://testnet.bscscan.com/tx/0x1f0a67af7cf0735e409dd2a0b273a0397b1aaccef1627e107126c8e2056f8b17)

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python demo.py    # generates a throwaway testnet wallet on first run
```

The live mainnet trading agent (this repo's root) carries its own TWAK-minted
ERC-8004 identity and attests every decision on it — see the main README.
