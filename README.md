# Blob

Agent de trading autonome self-custody pour le [BNB Hack: AI Trading Agent Edition](https://dorahacks.io/hackathon/bnbhack-twt-cmc) (CoinMarketCap × Trust Wallet × BNB Chain) — Track 1, Autonomous Trading Agents.

> **Statut : pipeline paper fonctionnel + backtest.** Data → stratégie → risk → ordres → exécution simulée, couvert par des tests unitaires ; backtest keyless (klines Binance + Fear & Greed historique) qui rejoue le code de décision de production. L'exécution live via TWAK CLI est écrite mais **non testée** (CLI non installé) ; la registration on-chain et l'intégration x402/ERC-8004 ne sont pas commencées. Voir [docs/redteam.md](docs/redteam.md) pour l'analyse de risques qui a fixé ces décisions.

## Utilisation

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m blob doctor     # vérifie la config (n'affiche jamais les secrets)
.venv/bin/python -m blob run-once   # un cycle complet (MODE=paper par défaut)
.venv/bin/python -m blob status     # valeur, drawdown, positions
.venv/bin/python -m blob backtest --days 90   # rejoue le code de décision sur l'historique (sans clé)
.venv/bin/python -m blob backtest --days 365 --compare   # baseline vs fast-lane, format compétition
.venv/bin/python -m blob loop       # runner 24/7 : cycle horaire, retries, alertes desktop
.venv/bin/pytest                    # tests
```

## Runbook semaine live (22-28 juin)

1. Lancer le runner via LaunchAgent (survit aux crashs et au login) :
   ```bash
   cp ops/com.blob.agent.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.blob.agent.plist
   ```
   Arrêt : `launchctl unload ~/Library/LaunchAgents/com.blob.agent.plist`
2. **La machine ne doit pas dormir** : `caffeinate -s` dans un terminal, ou réglages
   Économie d'énergie. Un jour sans trade = disqualification.
3. Vérification quotidienne (1 min) : `python -m blob status` + le trade du jour
   visible sur [BscScan](https://bscscan.com/address/0x84BFC511d8027337B285433f122880fB340f30B9),
   gas BNB > 0.001, et les pins du Telegram du hackathon.
4. Secours manuel si le runner est mort et qu'aucun trade n'est passé aujourd'hui :
   `twak swap USDT ETH --usd 1.10 --chain bsc` (puis investiguer).

## Architecture cible

```
CMC Agent Hub (MCP + x402) ──► datafeed ──► strategy (regime/momentum, déterministe)
                                                │
                                           risk engine (DD ladder -10%/-18%, allowlist
                                           ~20-30 tokens liquides, caps par trade/jour)
                                                │
                                           executor ── TWAK (signature locale, seule
                                                │       couche d'exécution; fallback
                                                │       PancakeSwap direct flaggé)
                                           scheduler (trade quotidien obligatoire
                                           00:30 UTC, retries, alerting)
```

## Décisions verrouillées (issues de la red team)

- **Spot only**, univers restreint aux tokens liquides de la liste éligible (149 BEP-20) — robuste au ruling perps en attente.
- **Turnover minimal** : 2-4 vraies rotations sur la semaine de trading + micro-trades de qualification quotidiens. Plancher de coût réel mesuré ~1.4 % round-trip → seuil d'entrée : edge attendu > 2 %.
- **Cœur déterministe**, LLM cantonné au scoring de données molles (sentiment/news), guardrails appliqués hors LLM avant signature.
- **Switch `MODE=paper|live`** dès le départ (règles de l'event encore mouvantes).
- **De-risking ladder** : -10 % → exposition réduite de moitié ; -18 % → tout en USDT jusqu'à la fin (DQ officielle ~30 %).
- Intégrations sponsors réelles uniquement : TWAK (exécution + guardrails + x402), CMC (data MCP + x402 payé en USDC sur Base), BNB Agent SDK (identité ERC-8004 de l'agent). Rien de cosmétique.

## Dates (2026)

| Échéance | Date |
|---|---|
| Inscription on-chain (`twak compete register`) | avant le 22 juin — **viser cette semaine** |
| Soumission DoraHacks (repo + stratégie) | 21 juin |
| Fenêtre de trading live | 22–28 juin (min 1 trade/jour, 7/7) |

## Prérequis (non commités)

Copier `.env.example` → `.env` et remplir :

- **TWAK** : Access ID + HMAC Secret depuis [portal.trustwallet.com](https://portal.trustwallet.com)
- **CMC** : clé API depuis [pro.coinmarketcap.com](https://pro.coinmarketcap.com) (crédits gratuits distribués aux participants via le Telegram du hackathon)
- **Wallet** : ~$12-15 USDT/ETH (BSC) + ~$3 BNB gas + ~$5 USDC (Base, pour x402)
