# Plan de route — Blob (mis à jour 11 juin 2026)

Inscription on-chain : ✅ faite (11 juin). Deadline soumission DoraHacks (les 2 tracks) : **21 juin**. Trading live : **22-28 juin**.

## Fait

- Pipeline complet data → stratégie → risk → ordres → exécution (paper testé live-API, TWAK live écrit + quote vérifié)
- Backtest format compétition (fenêtres 7j indépendantes, capital + pic frais) keyless
- Anti-churn (plancher de sortie + bonus de rétention), fast-lane implémenté (OFF par défaut, voir mémoire backtest)
- Check de risque horaire / rebalance quotidien (flaw DQ corrigé)
- Fixes revue adversariale : prix manquant → fallback dernier prix connu ; micro-trade de qualification quand 100 % déployé → vente d'un sliver ; sync holdings on-chain en mode live

## Chantiers restants

### 12-14 juin — intégrations sponsors + ops
1. ✅ **x402 dans la boucle de data** (10 pts rubrique TWAK) : implémenté (`blob/x402.py`,
   appelé au rebalance quotidien quand `X402_ENABLED=1`, plafonné par `--max-payment`,
   preuve loggée dans agent.jsonl). Découverte : le endpoint CMC x402 accepte le paiement
   **sur BSC** en stablecoin via EIP-3009 gasless (route "preferred") — pas besoin de Base.
   Reste : financer ~$5 du stablecoin de paiement (vérifier l'adresse du token
   0xcE24439F2D9C6a2289F741120FE202248B666666 "United Stables" avant d'acheter) et
   valider le shape de la réponse en payant une vraie requête.
2. **Identité ERC-8004** — décision : signature via `twak erc8004 register` (la clé reste
   dans TWAK, custody intacte ; le SDK Python `bnbagent` exige une private key brute,
   exclu pour le wallet de trading). Le SDK `bnbagent` sera utilisé pour l'agentURI,
   les lectures, et éventuellement une démo ERC-8183 sur testnet (gas-free MegaFuel)
   comme angle "inventif" du special BNB SDK.
3. ✅ **Scheduler 24/7** : primaire = **GitHub Actions** (cron horaire, gratuit repo public,
   état sur branche `agent-state`, wallet headless via `TWAK_WALLET_PASSWORD` — portabilité
   vérifiée) ; secours = LaunchAgent local `ops/com.blob.agent.plist` + `blob loop`.
   Un seul exécuteur live à la fois. Reste : créer les 5 secrets + 2 variables sur GitHub
   (action utilisateur) et valider un run via workflow_dispatch.

### 15-20 juin — répétition générale (le vrai détecteur de flaws)
4. Agent en paper 24/7 sans interruption ; chaque incident = un fix + un test.
5. **Premier swap réel** ~$2 dès que le wallet a un peu d'USDT (vérifie le bug Amber route en écriture + `twak wallet register` si les tokens n'apparaissent pas).
6. Script de mesure de coûts multi-tokens à nos tailles → recalibrer `min_momentum_pct`.
7. Surveiller les pins Telegram : % vs $ absolu, ~~perps~~ (résolu 12 juin : **spot only via
   l'interface swap TWAK** — trades hors TWAK probablement non comptés), modèle de
   coûts/fees (réponse promise par la team), double-track.

### 20-21 juin — soumission
8. Freeze du code, README anglais, strategy explainer (notre angle : risk-first, guardrails, survie).
9. **Démo vidéo** (OPTIONNELLE) : boucle self-custody de bout en bout, tx hash à l'écran.
   Les règles exigent "repo public + (lien démo OU vidéo OU instructions de setup)" → on a
   déjà repo + setup, la soumission est valide sans vidéo. La vidéo ne sert qu'au critère
   "Demo and presentation" des prix spéciaux (5 pts/100) et à la lisibilité jury. Polish, pas porte.
10. Soumission DoraHacks avant le 21 ; funding USDT final avant le 22 00:00 UTC.

### 22-28 juin — semaine live
11. Monitoring quotidien (trade de qualification vérifié on-chain chaque jour, gas BNB, drawdown).
12. Décision fast-lane ON/OFF selon le régime d'ouverture (justifiée dans l'explainer si activée).
