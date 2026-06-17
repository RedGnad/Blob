"""A trustless agent-to-agent alpha market on ERC-8183.

Blob sells its regime/momentum signal to another agent through an ERC-8183 job
escrow. Two trustless layers stack:
  1. ERC-8183 escrow  -> the PAYMENT is trustless (funds released only on
     delivery; silence past the dispute window approves, a dispute triggers a
     voter quorum).
  2. recompute-able attestation -> the DELIVERY QUALITY is trustless: the
     on-chain deliverable is keccak256 of a manifest whose metadata carries the
     signal's raw inputs, so the buyer recomputes the signal itself and checks
     the seller fabricated nothing.

=> agent-to-agent alpha that the buyer can trust without trusting the seller.

Standalone on BSC testnet, isolated from the live Blob agent (the SDK needs a
raw key, incompatible with TWAK's no-export model — see README). Requires the
BUYER wallet to hold a little tBNB (gas for the faucet claim + ERC-20 approve;
MegaFuel does not sponsor non-SDK contracts) and 10 U from the faucet.

Run:
    python claim_u.py     # once the buyer has tBNB: pulls 10 U from the faucet
    python market.py      # drives the full buy -> deliver -> settle + verify
"""

from __future__ import annotations

import base64
import json
import time

from bnbagent.erc8183 import DeliverableManifest, ERC8183Client, JobStatus
from bnbagent.wallets import EVMWalletProvider

import signal as alpha  # local signal.py

CHAIN_ID = 97
TESTNET_TX = "https://testnet.bscscan.com/tx/"


def main() -> None:
    buyer = EVMWalletProvider(password="demo-buyer", persist=True, wallets_dir=".wallet-buyer")
    blob = EVMWalletProvider(password="demo-blob", persist=True, wallets_dir=".wallet-blob")
    buyer_c = ERC8183Client(buyer, network="bsc-testnet")
    blob_c = ERC8183Client(blob, network="bsc-testnet")
    print(f"buyer={buyer.address}  blob/provider={blob.address}")

    # 1. Blob computes the alpha it sells, and its attestation digest.
    payload = alpha.compute_signal()
    sig_digest = alpha.digest(payload)
    print(f"signal: {payload['signal']}  attestation={sig_digest}")

    budget = 1 * (10 ** buyer_c.token_decimals())
    expired_at = int(time.time()) + 65 * 60

    # 2. Buyer opens the escrow naming Blob as provider, then funds it.
    res = buyer_c.create_job(
        provider=blob.address,
        expired_at=expired_at,
        description=f"regime/momentum signal; attestation={sig_digest}",
    )
    job_id = res["jobId"]
    print(f"create_job  job_id={job_id}  {TESTNET_TX}{res.get('transactionHash')}")
    print(f"register_job  {TESTNET_TX}{buyer_c.register_job(job_id).get('transactionHash')}")
    buyer_c.set_budget(job_id, budget)
    print(f"fund  {TESTNET_TX}{buyer_c.fund(job_id, budget).get('transactionHash')}")

    # 3. Blob delivers: a manifest whose hash is the on-chain deliverable and
    #    whose self-contained data: URL lets anyone recompute the signal.
    manifest = DeliverableManifest(
        version=1,
        job_id=job_id,
        chain_id=CHAIN_ID,
        contracts={"commerce": blob_c.network.commerce_contract},
        response={"regime": payload["signal"]["regime"], "pick": payload["signal"]["pick"]},
        metadata={"payload": payload, "attestation": sig_digest},
    )
    deliverable = manifest.manifest_hash()
    manifest_json = json.dumps(manifest.to_dict(), sort_keys=True, separators=(",", ":"))
    data_url = "data:application/json;base64," + base64.b64encode(manifest_json.encode()).decode()
    sub = blob_c.submit(job_id, deliverable, {"deliverable_url": data_url})
    print(f"submit  deliverable=0x{deliverable.hex()}  {TESTNET_TX}{sub.get('transactionHash')}")

    # 4. Settle (permissionless). OptimisticPolicy: silence past the dispute
    #    window approves. On first run, confirm the window length on testnet and
    #    wait it out if settle does not move the job to COMPLETED immediately.
    settle = buyer_c.settle(job_id)
    status = buyer_c.get_job_status(job_id)
    print(f"settle  {TESTNET_TX}{settle.get('transactionHash')}  status={status}")

    # 5. Recompute-it-yourself: integrity (manifest hash) + quality (signal).
    fetched = json.loads(manifest_json)
    integrity = DeliverableManifest.from_dict(fetched).manifest_hash() == deliverable
    quality = alpha.recompute_and_verify(
        fetched["metadata"]["payload"], fetched["metadata"]["attestation"]
    )
    print(f"verify  manifest_integrity={integrity}  signal_recompute={quality}")
    if status == JobStatus.COMPLETED and integrity and quality:
        print("TRUSTLESS ALPHA DELIVERED: paid on delivery, quality recompute-verified.")


if __name__ == "__main__":
    main()
