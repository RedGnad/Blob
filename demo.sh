#!/bin/bash
# Blob — one-command demo for the submission video.
# Record your screen, run `./demo.sh`, and press Enter to move between steps.
# Everything here is safe: paper mode, no funds spent, no live swap.
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python
banner() { printf '\n\033[1;36m========================================================\n  %s\n========================================================\033[0m\n\n' "$1"; }
pause() { printf '\n\033[2m   [ press Enter ]\033[0m'; read -r _; }

clear
banner "BLOB — a self-custody trading agent you can VERIFY"
echo "   Trades live on BNB Chain. Keys never leave the wallet."
echo "   Every decision is committed on-chain. Don't trust it — verify it."
pause

banner "1/5  Verify our on-chain proof yourself — no key, no trust"
$PY verify.py
pause

banner "2/5  One real decision (data -> regime -> orders)"
echo "   Reads CoinMarketCap, picks an exposure, plans trades:"
$PY -m blob run-once 2>/dev/null | $PY -c "import json,sys;d=json.load(sys.stdin);print('   exposure:',d['exposure']);print('   regime + picks:');[print('     -',r) for r in d['reasons']];print('   trades executed:',d['orders_executed'])"
pause

banner "3/5  Engineered to survive — 358 competition-format windows"
$PY -m blob backtest --days 365 2>/dev/null | $PY -c "import json,sys;r=json.load(sys.stdin)['competition_windows_7d'];print(f\"   median {r['median']*100:.1f}%   p90 +{r['p90']*100:.0f}%   max +{r['max']*100:.0f}%\");print(f\"   worst drawdown {r['worst_window_drawdown']*100:.0f}%   DISQUALIFICATIONS: {r['dq_rate']*100:.0f}%\")"
pause

banner "4/5  Deep CoinMarketCap Agent Hub — runs an official CMC Skill"
$PY -m blob market-scan 2>/dev/null | $PY -c "import json,sys;d=json.load(sys.stdin)['analysis'];print('   skill:',d.get('skill'));print('   MCP tools used:',len(d.get('mcp_tools_consumed',[])));print('   read:',d.get('synthesis'))"
pause

banner "5/5  A trustless alpha market — Blob sells its signal on ERC-8183"
echo "   The buyer recomputes the signal from committed inputs and verifies it:"
$PY bnb-sdk-demo/signal.py 2>/dev/null | tail -3
pause

banner "All of it is real and on-chain (BSC) — click to confirm"
echo "   agent wallet   https://bscscan.com/address/0x84BFC511d8027337B285433f122880fB340f30B9"
echo "   ERC-8183 market (testnet)  https://testnet.bscscan.com/tx/8df4e1a2ad5893b920e68cc1767db2c4c7e8f304fd352bec4510d923ae6a125d"
echo
echo "   Self-custody. On-chain. Verifiable.   Blob."
echo
