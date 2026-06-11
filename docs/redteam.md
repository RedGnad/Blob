# Red team — Blob (I2 "risk-first TWAK-natif") × Track 1

Date : 11 juin 2026. Sources : règles DoraHacks, FAQ + conversation Telegram du hackathon, BscScan (contrat CompetitionRegistry), docs TWAK/CMC/BNB Agent SDK.

Statut du projet à cette date : **pré-implémentation** (aucun code, décisions d'architecture seulement).

## 🔴 Critiques — peuvent invalider la candidature ou l'EV

### R1. Le mode de classement (% vs $ absolu) n'est pas officiellement tranché
La FAQ dit « ranked by total return » (= %), mais des participants contestent l'absence de capital de départ normalisé et les organisateurs « compilent les réponses ». Si le classement était en $ absolu, un capital de ~$15 rend le Track 1 injouable.
- **Mitigation** : surveiller les pins Telegram quotidiennement ; architecture inchangée dans les deux cas ; si $ absolu est confirmé → pivot : abandonner l'ambition placement, garder uniquement specials (TWAK/SDK/Hub, jugés au panel, insensibles au capital) + Track 2 si autorisé.
- **Trigger de décision** : toute annonce officielle sur le scoring avant le 21 juin.

### R2. Fiabilité d'exécution TWAK sur BSC (bug avéré)
Signalé dans le Telegram : l'endpoint Amber route renvoie `code: 13 internal server error` sur des requêtes de swap BSC valides. Question ouverte : un trade direct via le router PancakeSwap depuis le wallet enregistré compte-t-il pour le scoring ?
- **Mitigation** : tester la boucle swap TWAK complète dès l'obtention des credentials (plusieurs jours avant le 22) ; retry ladder + alerte ; fallback signing direct PancakeSwap derrière un flag `EXECUTOR_FALLBACK`, utilisé uniquement si TWAK est indisponible un jour de trade obligatoire (le scoring PnL est basé sur le portefeuille du wallet, pas sur la route — mais le special TWAK exige « TWAK as sole execution layer » : logger chaque usage du fallback et le déclarer honnêtement dans la soumission).

### R3. Échec du trade quotidien obligatoire = perte de qualification
7/7 jours requis. Un serveur down, un bug, un endpoint TWAK en panne un seul jour suffit.
- **Mitigation** : trade obligatoire micro exécuté tôt (00:30 UTC) indépendamment du signal ; vérification du receipt on-chain ; retry jusqu'à succès avec escalade (notification téléphone) ; deuxième scheduler indépendant en filet de sécurité ; runbook manuel (commande CLI en une ligne) si tout échoue.

### R4. Modèle de coûts simulés inconnu
Le staff a confirmé que le scoring utilise des coûts **simulés**, pas les quotes TWAK live (~1.4 % round-trip mesuré par un participant). Trois variantes possibles : % flat par trade, pénalité fixe, ou simulé **en plus** des coûts réels (double peine).
- **Mitigation** : stratégie robuste aux trois : turnover minimal (2-4 vraies rotations sur la semaine + micro-trades de qualification), seuil d'entrée = edge attendu > 2 % par rotation. Recalibrer dès publication du modèle.

## 🟠 Majeurs

### R5. Plancher de coût réel ~1.4 % round-trip
Mesuré sur ETH/USDT via TWAK (12 échantillons, stable 0.1→10 ETH ; gas négligeable). Le momentum à horizon 1 semaine est essentiellement du bruit face à ce plancher.
- **Adaptation** : viser des moves 3-5 % (trend/regime, pas du scalp) ; hysteresis sur les rebalances (on ne sort/entre que si le signal traverse un seuil avec marge) ; le trade quotidien obligatoire est une contrainte de qualification, pas un levier de score (confirmé par le staff) → taille minimale.

### R6. Ambiguïtés sur les actifs comptés
BNB/WBNB ne figure pas dans la liste des 149 tokens in-scope (à re-vérifier sur la liste officielle) ; le traitement des tokens résiduels et de W/BNB est une question ouverte posée dans le Telegram.
- **Mitigation** : garder la valeur du portefeuille en tokens in-scope non ambigus (USDT, ETH) ; BNB uniquement pour le gas, au minimum ; pas de positions résiduelles exotiques au moment des marks horaires.

### R7. Tokens piégeux dans la liste éligible
La liste contient des tokens à transfer-tax, low-liquidity ou exotiques (SMILEK, GUA, CHEEMS, 币安人生…). Slippage réel énorme, voire honeypot-like.
- **Mitigation** : allowlist restreinte à ~20-30 tokens vérifiés (liquidité PancakeSwap, pas de taxe) codée dans les guardrails TWAK — double bénéfice : sécurité + points rubrique TWAK (« token allowlists » = critère explicite des 20 pts guardrails).

### R8. Règles mouvantes en cours d'event — partiellement résolu (12 juin)
~~Perps : ruling « en confirmation »~~ → **tranché par la team BNB (Telegram, 12 juin) : spot only, via l'interface de swap TWAK**. Notre design spot-only TWAK-first était déjà conforme. Conséquence importante : les trades hors interface TWAK (PancakeSwap direct) risquent de ne pas compter au scoring → le fallback `EXECUTOR_FALLBACK` est rétrogradé à assurance-qualification de dernier recours (mieux vaut un retry TWAK qu'un trade hors-scoring). Le modèle de frais reste en attente (« I asked and will let you know »).
- **Mitigation restante** : switch `MODE=paper|live` ; aucune dépendance à une règle non confirmée ; recalibrer les coûts dès l'annonce des fees.

### R9. Wallets concurrents publics (et le nôtre aussi)
Le contrat d'inscription est public : nos trades sont copiables en live, et inversement on peut monitorer les agents rivaux pendant la semaine.
- **Évaluation** : risque faible à notre taille (copier un wallet de $15 n'intéresse personne) ; l'opportunité inverse (meta-game) est du scope creep — ne pas construire avant que le core soit fiable.

## 🟡 Modérés

### R10. x402 réel = USDC sur Base
Le x402 de CMC paie $0.01 USDC/requête **sur Base** (EIP-3009, pas de gas requis). Sans ~$3-5 d'USDC sur Base, le critère x402 de la rubrique TWAK (10 pts) vaut 0 — « real, not a README mention ».
- **Mitigation** : budgéter $5 USDC sur Base ; utiliser les crédits CMC gratuits (distribués aux participants via le Telegram) pour le bulk, x402 pour un sous-ensemble réel de la boucle de trade, loggé et démontrable.

### R11. Drawdown mesuré sur marks horaires
Un kill-switch à 15 % sacrifie de l'upside alors que la DQ est à ~30 %.
- **Décision** : ladder de de-risking : -10 % → réduction d'exposition de moitié ; -18 % → kill-switch (tout en USDT + micro-trades de qualification jusqu'à la fin). Marge de 12 points sur la DQ.

### R12. Non-déterminisme LLM dans la boucle
Un LLM qui décide librement = comportement non reproductible, risque de tail event (cf. GPT-5 à -75 % sur Alpha Arena).
- **Décision** : cœur de décision déterministe (règles regime/momentum) ; LLM cantonné à l'interprétation de données molles (sentiment, news) avec sortie bornée à un score ; guardrails (caps, allowlist, DD ladder) appliqués **hors** LLM, en dernier ressort avant signature.

### R13. Concurrence sérieuse visible
Le Telegram montre au moins une équipe méthodique (mesures de coûts publiées). Le special TWAK ne sera pas vacant ; le special BNB SDK reste le moins disputé.
- **Évaluation** : maintien des cibles ; la qualité moyenne du field reste basse (faucet-begging, bans CAS).

## Questions ouvertes à suivre (pins Telegram)
1. Classement % vs $ absolu (R1) — **bloquant pour l'allocation d'effort**
2. Perps ou spot-only (R8)
3. PancakeSwap direct éligible au scoring (R2)
4. Modèle de coûts simulés (R4)
5. Double-track T1+T2 par la même équipe
6. Traitement W/BNB et tokens résiduels (R6)

## Capital (décision)
Classement en % (sous réserve R1) → le capital n'influence pas le score ; les whales à $10k n'ont aucun avantage de classement (et plus d'impact AMM que nous). $1 est exclu : la règle « heure démarrant ≤$1 = 0 % » + dust + gas rendent le compte instantanément fragile. **Budget : ~$25-30 total** — $12-15 USDT/ETH (trading), ~$3 BNB (gas), ~$5 USDC sur Base (x402).
