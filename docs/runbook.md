# Runbook — semaine live (22-28 juin 2026)

## Bascule en live (le 22 juin avant 00:00 UTC)

```bash
gh variable set AGENT_MODE --body live          # le scheduler cloud passe en réel
launchctl unload ~/Library/LaunchAgents/com.blob.agent.plist   # un seul exécuteur live
gh workflow run agent                            # cycle immédiat pour valider
```

Règle : **un seul exécuteur en mode live**. Le cloud (GitHub Actions) est primaire ;
le Mac reste en secours déchargé.

## Vérification quotidienne (1 minute)

1. [Actions](https://github.com/RedGnad/Blob/actions) : runs verts ? (email automatique sinon)
2. Le trade du jour est passé ? → [BscScan du wallet](https://bscscan.com/address/0x84BFC511d8027337B285433f122880fB340f30B9)
   ou `git show origin/agent-state:live_portfolio.json` (champ `last_trade_date`)
3. Gas : balance BNB > 0.001 (`twak balance --chain bsc --address 0x84BF... --json`)
4. Drawdown : si > 10 %, la ladder a déjà réduit l'exposition — ne pas intervenir à chaud.
5. Pins Telegram du hackathon (changements de règles, annonce fees).

## Secours manuel

Si GitHub Actions est en panne un jour de trade obligatoire :

```bash
# Option 1 : réactiver l'agent local (et le décharger une fois GitHub revenu)
launchctl load ~/Library/LaunchAgents/com.blob.agent.plist
caffeinate -s &   # empêcher le sommeil du Mac

# Option 2 : trade de qualification à la main (dernier recours)
twak swap USDT ETH --usd 1.10 --chain bsc
```

## Fin de concours (après le 28 juin)

- Repasser `AGENT_MODE` à `paper`, vider le wallet vers une adresse sûre,
  révoquer les secrets GitHub (`gh secret delete ...`).
