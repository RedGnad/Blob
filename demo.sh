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

banner "2/5  One real decision — reads the market, decides how much to risk"
echo "   (risk-off regime => it stays in cash; risk-on => it deploys into momentum)"
echo "   ... reading live CoinMarketCap data (a few seconds) ..."
$PY -m blob run-once --rebalance 2>/dev/null | $PY -c "import json,sys;d=json.load(sys.stdin);print('   exposure: %.0f%% in the market' % (d['exposure']*100));print('   regime + picks:');[print('     -',r) for r in d['reasons']];print('   trades executed:',d['orders_executed'])"
pause

banner "3/5  Engineered to survive — backtested on a full year of real data"
$PY -c "import json;r=json.load(open('backtest-results.json'));print(f\"   DISQUALIFICATIONS (drawdown blow-ups): {r['dq_rate']*100:.0f}%\");print(f\"   typical week {r['median']*100:.1f}%   best week +{r['max']*100:.0f}%   worst drawdown {r['worst_window_drawdown']*100:.0f}%\");print('   reproduce: python -m blob backtest --days 365')"
pause

banner "4/5  Deep CoinMarketCap Agent Hub — runs an official CMC Skill"
$PY -c "import json;d=json.load(open('marketscan-sample.json'));print('   loads the official CMC Skill:',d['skill']['name'],'(from CMC repo)');print('   MCP tools executed:',d['mcp_tools']);print('   market read:',d['synthesis']);print('   reproduce: python -m blob market-scan')"
pause

banner "5/5  A trustless alpha market — Blob sells its signal on ERC-8183"
echo "   The buyer recomputes the signal from committed inputs and verifies it:"
$PY bnb-sdk-demo/signal.py 2>/dev/null | grep -E "digest:|verify:" | sed 's/^/   /'
pause

banner "All of it is real and on-chain (BSC) — click to confirm"
echo "   agent wallet   https://bscscan.com/address/0x84BFC511d8027337B285433f122880fB340f30B9"
echo "   ERC-8183 market (testnet)  https://testnet.bscscan.com/tx/8df4e1a2ad5893b920e68cc1767db2c4c7e8f304fd352bec4510d923ae6a125d"
echo
echo "   Self-custody. On-chain. Verifiable.   Blob."
echo
