"""Pull 10 test "U" tokens from the public faucet into the buyer wallet.

MegaFuel does not sponsor non-SDK contracts (verified: isSponsorable -> False),
so the buyer must hold a little tBNB for gas before running this. Get tBNB from
https://www.bnbchain.org/en/testnet-faucet for the buyer address printed below.
"""

from __future__ import annotations

from bnbagent.wallets import EVMWalletProvider
from web3 import Web3

RPC = "https://bsc-testnet-dataseed.bnbchain.org"
FAUCET = Web3.to_checksum_address("0x86e9197CC0F76E4e4aaa7082180945196bBAb5D3")
U_TOKEN = Web3.to_checksum_address("0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565")
ABI = [
    {"inputs": [], "name": "requestTokens", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "a", "type": "address"}], "name": "allowedToWithdraw",
     "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
]
ERC20_BAL = [{"inputs": [{"name": "a", "type": "address"}], "name": "balanceOf",
              "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"}]


def _poa_web3() -> Web3:
    """BSC is proof-of-authority: inject the POA middleware (name differs across
    web3 v6/v7) so extraData validation passes."""
    w3 = Web3(Web3.HTTPProvider(RPC))
    try:
        from web3.middleware import ExtraDataToPOAMiddleware
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except ImportError:
        from web3.middleware import geth_poa_middleware
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3


def main() -> None:
    buyer = EVMWalletProvider(password="demo-buyer", persist=True, wallets_dir=".wallet-buyer")
    w3 = _poa_web3()
    acct = w3.eth.account.from_key(buyer.export_private_key())
    print(f"buyer={acct.address}  tBNB={w3.from_wei(w3.eth.get_balance(acct.address), 'ether')}")

    faucet = w3.eth.contract(address=FAUCET, abi=ABI)
    if not faucet.functions.allowedToWithdraw(acct.address).call():
        print("not eligible yet (faucet cooldown).")
        return

    tx = faucet.functions.requestTokens().build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": 97,
        "gas": 200_000,
    })
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"claim tx: https://testnet.bscscan.com/tx/{h.hex()}")
    w3.eth.wait_for_transaction_receipt(h)
    bal = w3.eth.contract(address=U_TOKEN, abi=ERC20_BAL).functions.balanceOf(acct.address).call()
    print(f"U balance: {bal / 1e18}")


if __name__ == "__main__":
    main()
