# Rapport pour l'advisor — Blob × BNB Hack: AI Trading Agent Edition

État au 16 juin 2026. Soumission DoraHacks le 21, trading live 22-28, jugement 29 juin-5 juillet.
Repo public : https://github.com/RedGnad/Blob — wallet agent `0x84BFC511d8027337B285433f122880fB340f30B9` (inscrit on-chain).

But du rapport : audit honnête de notre position vs le scoring réel, avec les écarts non maximisés
explicités. Pas de cheerleading — chaque claim est tracé à une preuve ou signalé comme manquant.

---

## 1. Ce qui est construit et VÉRIFIÉ (preuves on-chain)

| Élément | Preuve |
|---|---|
| Inscription concours (contrat CompetitionRegistry) | tx `0x9bfc02…ae0fbc` |
| Swap TWAK aller (USDT→ETH) | tx `0x080ddd…90b877` |
| Swap TWAK retour (ETH→USDT) | tx `0xeda75e…2ae4c0` |
| x402 payé en USDT sur BSC (Permit2) | tx `0x2b6888…397bfd` |
| Identité ERC-8004 mintée (agentId 132858) | tx `0x14a6f4…a25103` |
| Cycle live autonome de bout en bout (smoke test) | tx `0xa07d1d…4169` |

Mécanique : pipeline déterministe data (CMC) → régime (BTC 7j + Fear&Greed) → sélection momentum
cost-aware → risk engine (ladder drawdown -10%/-18%, allowlist 15 tokens, clamps de solde, slippage)
→ exécution TWAK seule couche. Scheduler cloud GitHub Actions (boucle interne 30 min pour battre le
throttling ~2h de GitHub) + secours local. 34 tests unitaires. Journal d'audit horaire persistant.

## 2. Backtest (format compétition, keyless, reproductible)

358 fenêtres de 7 jours indépendantes (capital + pic de drawdown frais par fenêtre = le vrai format),
sur une année à ETH -42% : **médiane -1.7%, p90 +6.7%, max +20.6%, 0 disqualification, pire
drawdown 21.5%, ~6 trades/fenêtre.** Coûts d'exécution réels mesurés par token (1.27-3.36%, médiane 1.4%).

Lecture honnête : c'est une distribution à **queue gauche protégée, upside modéré**. On ne prétend pas
à un alpha. La thèse est la survie relative dans un field où beaucoup se disqualifient.

## 3. Carte du scoring — où on est fort, où on ne l'est PAS

### Track 1 (placement, $24k, PnL pur) — fort en défense, faible en upside
Classé sur le return total, gate drawdown ~30%. Notre profil maximise la **non-disqualification** et le
**placement relatif en semaine baissière** (≈0% quand la moitié du field saigne ou explose). 
**Non maximisé pour le top 1-2** : un agent agressif en semaine haussière nous bat. Choix d'EV assumé.
→ Cible réaliste : **3e-5e** ($2-4k), improbable au-dessus.

### Special "Best Use of TWAK" ($2k) — NOTRE POINT FORT
Rubrique publiée, on coche le cœur pondéré :
- Profondeur TWAK (30) : 4 surfaces réelles — swaps, x402, ERC-8004, wallet/portfolio. **Fort.**
- Intégrité self-custody (25) : clés jamais exportées, signature locale via TWAK sur toute la boucle.
  **Fort** — *nuance honnête : le wallet chiffré + password vivent dans les secrets GitHub pour le
  cloud ; ce n'est pas une rupture du modèle (aucun co-signataire/custodian), mais un juge strict
  pourrait le noter. Reste self-custodial au sens de la rubrique.*
- Autonomie + guardrails (20) : ladder drawdown, allowlist, clamps, slippage, trade quotidien. **Fort.**
- x402 natif (10) : paiement réel $0.01/jour dans la boucle, prouvé on-chain. **Fort.**
- Originalité/pertinence (10) : "risk-first survival agent". **Moyen** (pas révolutionnaire).
- Demo (5) : preuves on-chain OK, vidéo à faire. **À compléter.**
→ Estimation : ~75/100 sur le cœur pondéré. **Meilleur EV du projet.**

### Special "Best Use of Agent Hub" ($2k) — FAIBLE, non maximisé
On utilise une **tranche mince** du CMC Agent Hub : quotes spot + Fear&Greed + endpoint x402.
Le Hub offre bien plus : MCP, CLI, Skills library, dérivés (funding rates), social, KOLs, news.
Une équipe exploitant funding rates + social + Skills nous bat sur CE prix. **Lever non tiré.**

### Special "Best Use of BNB AI Agent SDK" ($2k) — FAIBLE, non maximisé
On a minté l'identité ERC-8004 via `twak erc8004`, **pas** via le SDK Python `bnbagent` lui-même.
Le prix récompense "the most inventive integration of the SDK" — qu'on n'utilise pas réellement.
**Lever non tiré** (envisagé : démo ERC-8183 sur testnet gas-free, non construite).

### Track 2 (Strategy Skills, $6k) — NON ENGAGÉ
On n'a pas construit de Skill CMC. Or notre moteur de backtest EST quasiment une spec de stratégie
backtestable. Si le double-track (T1+T2 même équipe) est autorisé — **question ouverte non tranchée
sur le Telegram** — c'est de l'EV bon marché laissé sur la table (pool $6k, barre d'entrée basse).

## 4. Leviers pour maximiser l'EV total (à arbitrer par l'advisor)

| Levier | Effort | Gain potentiel | Risque |
|---|---|---|---|
| A. Skill Track 2 dérivé du backtest existant | ~1-2 j | pool $6k, panel barre basse | nécessite confirmer double-track (Telegram) |
| B. Élargir l'usage CMC Hub (funding rates / social-divergence) | ~1-2 j | special Agent Hub + signal stratégie | risque d'overfit avant le live |
| C. Vraie intégration `bnbagent` SDK (démo ERC-8183 testnet) | ~1 j | special BNB SDK (peu disputé) | scope, gas-free testnet OK |
| D. Affûter le récit d'originalité/adoption | ~0.5 j | points panel "originality/relevance" | faible |
| E. Vidéo démo (boucle self-custody + tx hash) | ~1 h | 5 pts "demo" des specials | aucun |

Note EV : la vidéo (E) et le récit (D) sont quasi-gratuits. Le Skill Track 2 (A) est le plus gros gain
brut mais conditionné au double-track. B et C renforcent des specials où on est aujourd'hui faibles.

## 5. Inconnues externes (hors de notre contrôle, à surveiller)

1. **Modèle de coûts/fees simulés** — promis par la team, non publié. Touche le recalibrage du seuil
   d'entrée (paramétré, 5 min). 
2. **Classement % vs $ absolu** — non confirmé officiellement (notre design marche dans les deux cas).
3. **Double-track T1+T2 autorisé ?** — conditionne le levier A.
4. **Fiabilité cloud sur 7 jours en live** — validé en paper + 1 cycle live ; pas encore éprouvé en
   live continu (choix assumé : éviter de brûler du spread réel hors fenêtre de scoring).
5. **Gas BNB** — $1.45 en réserve, ~$0.02/swap, suffisant pour la semaine ; à monitorer.

## 6. Synthèse pour décision

**Maximisés** : special TWAK (cœur de notre EV) + survie/placement Track 1 en semaine défavorable.
**Non maximisés** : specials Agent Hub et BNB SDK (usage mince), Track 2 (non engagé), top 1-2 Track 1.

Question stratégique à trancher : **rester focalisé "TWAK + survie" (profond mais étroit)**, ou
**élargir vers Track 2 + Agent Hub + SDK (plus de tickets de loterie panel, au prix de dispersion et
de risque sur le core)** ? Avec ~5 jours avant soumission et 1 seul builder, l'arbitrage effort/dispersion
est réel. Recommandation interne : E + D (gratuits), puis A si double-track confirmé, puis C ; B en dernier
(risque overfit le plus élevé avant le live).

---

## ADDENDUM (16 juin) — Renseignement Telegram + analyse concurrentielle

### Signaux confirmés (qui parle : staff vs participant)
- **Spot only** : re-confirmé plusieurs fois (participants, cohérent avec ruling staff antérieur). ✅ aligné.
- **Classement en %** : participants l'affirment ("obviously it's %"), cohérent avec "ranked by total
  return" de la page. Toujours pas de confirmation staff écrite noir sur blanc. ⚠️ à verrouiller.
- **Double-track T1+T2** : "I think you can" (participant) + message staff antérieur (gwen) "same deadline
  for both tracks, just for track 1 you have to make the agent trade". Signal **modérément fort que c'est
  autorisé**, MAIS la page dit "Pick one". Tension non résolue → **demander confirmation explicite staff
  avant d'investir dans Track 2.**
- **BNB hors whitelist** : question posée, sans réponse claire ; notre design (BNB = gas only) est déjà bon.
- **Real BNB requis pour la semaine live** : confirmé. ✅ on a la réserve.
- **Pas de clés API dans le repo public** : ordre staff (Gwen). ✅ on est déjà conformes (secrets GH, .env
  gitignore) — un pan du field va se faire avoir là-dessus.

### Faiblesse du field = notre moat (important)
- **TWAK swap renvoie 403 Forbidden** pour plusieurs participants sur le plan free ("works for read,
  403 on swap"). **NOS swaps fonctionnent** (tx réelles prouvées) → une partie du field pourrait être
  **incapable d'exécuter le moindre trade live**. Ça **augmente mécaniquement nos chances de placement
  Track 1** (moins de concurrents fonctionnels). À surveiller : que notre accès reste actif.
- **Agent Hub difficile à câbler** : beaucoup galèrent (MCP endpoint, x402, accès Pro). Notre x402 +
  REST fonctionnels nous mettent devant la médiane — mais la profondeur Hub reste le critère du special.

### Concurrents identifiés (menace réelle, pas le tout-venant)
- **Brandon M. / BinacciAI** (github.com/BinacciAI/trading-agent) : "pipeline de 6 agents, 7+ Skills",
  "institutional quant level", open-source, calcule fees/gas + maker/taker. Va **large** (Track 2 Skills
  + Track 1). **Menace sérieuse sur les prix panel et Track 2.** On ne peut pas le battre en largeur.
- **VPAY / Ananse** (Track 2, github.com/yooplvy/ananse-attestable-regime-skill) : Skill "regime
  attestable" qui orchestre le Agent Hub (find_skill→execute_skill, btc_cross_asset_correlation) et
  **commit chaque signal on-chain (keccak256)**, abstention si Hub bloqué. **Original et soigné** —
  fort sur le special Agent Hub et Track 2.

### Lecture concurrentielle
Le **top du field va large et exploite le Agent Hub Skills à fond** (exactement nos 2 specials faibles).
On **ne peut pas les battre en largeur** (1 builder, 5 jours). Notre edge défendable : **profondeur TWAK
self-custody** (Brandon fait du quant multi-agent mais rien n'indique une intégration TWAK aussi profonde ;
Ananse est Track 2 pur sans exécution). Le special TWAK reste notre meilleure prise à haute confiance.

### Réponse directe aux 3 questions
1. **Est-ce le plus optimal ?** Pour le special TWAK + survie Track 1 : oui, c'est notre edge défendable.
   Pour "gagner le PLUS" (EV total tous prix) : **non** — on laisse Track 2 ($6k) et 2 specials sur la table.
2. **Utilise-t-on tous les outils ?** **Non.** TWAK : à fond (bien). CMC Agent Hub : tranche mince
   (pas de funding rates / social / Skills / MCP). BNB SDK : pas vraiment utilisé. C'est l'écart honnête.
3. **Prêt à gagner le plus ?** Prêt à concourir fort pour **1 special + 1 placement Track 1**. Pour
   maximiser le total : confirmer double-track → **construire un vrai Skill Track 2 utilisant le mécanisme
   Agent Hub Skills** (ouvre $6k + renforce le special Agent Hub). Mais ne PAS courir après la largeur de
   Brandon — garder la profondeur TWAK comme ancre.

### Recommandation révisée (par EV/effort, 5 jours, 1 builder)
1. **Verrouiller 3 réponses staff sur Telegram** (gratuit, débloque tout) : double-track ? classement %/$ ?
   modèle de fees ? — ces réponses orientent 50% de la décision.
2. **Vidéo + récit adoption** (E+D, ~quasi gratuit, points specials).
3. **SI double-track confirmé : Skill Track 2** dérivé de notre moteur, mais branché sur le **mécanisme
   Agent Hub Skills** (find_skill/execute_skill) pour faire d'une pierre deux coups (Track 2 + special
   Agent Hub). ~1.5 j. C'est le plus gros gain d'EV incrémental.
4. **Protéger le moat TWAK** : ne rien casser sur le core, finir la semaine live proprement.
5. **NE PAS** sur-enrichir les signaux live avant le 22 (overfit > gain). Le faire éventuellement
   dans le Skill Track 2 (backtest, pas d'argent réel en jeu).
