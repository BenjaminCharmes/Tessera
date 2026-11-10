---
agent: codeur
created: 2026-11-09
depends_on:
- ticket-894
estimated_days: 1
id: ticket-896
pr_number: 1004
priority: medium
status: done
title: A setup script recreates the agent account on any PC, admin part kept minimal
type: chore
---

# ticket-896 — Un script recrée le compte agent sur n'importe quel PC, avec une partie admin minimale

## Objectif

Que Benjamin puisse installer l'isolation des agents sur un autre poste en
quelques commandes, et vérifier ce qui manque au compte agent sans deviner.

## Contexte

La phase 0 du 09/11 a été faite par des scripts manuels, corrigés en route :
- sur le PC de Benjamin, son compte n'est **pas** administrateur ; une fenêtre
  élevée tourne sous un autre compte (`admin.consultant`), avec un autre profil
  et un autre coffre. La partie admin ne doit donc rien lire ni écrire dans le
  profil de l'utilisateur ;
- la partie admin se limite à : créer le compte, le masquer de l'écran de
  connexion, créer `C:\ProgramData\Tessera\bin` avec `M` pour l'utilisateur et
  `RX` pour l'agent, et remettre le mot de passe par un fichier lisible par
  l'utilisateur seul ;
- la partie utilisateur range le mot de passe dans le coffre et efface le
  fichier par `[IO.File]::Delete` (`Remove-Item -Force` exige le droit de changer
  les attributs, que l'utilisateur n'a pas), copie le CLI, donne `RX` sur les
  outils (`scoop\apps`, `uv\python`, `.local\bin`) ;
- l'authentification : `claude setup-token` sous le compte de l'utilisateur, puis
  le jeton est lu dans le presse-papiers **après** le lancement du script (copier
  la commande avant écrase le jeton), rangé sous `AGENT_OAUTH_TOKEN`, presse-papiers
  vidé ; une saisie masquée de Windows PowerShell 5.1 ignore Ctrl+V ;
- `New-LocalUser -Description` est limité à 48 caractères.

Les scripts de référence sont dans `~/.tessera/worktrees/manuel/phase0-isolation/`
(`phase0-admin.ps1`, `phase0-moi.ps1`, `phase0-jeton-agent.ps1`, `phase0-preuve.ps1`).

## Solution proposée

- `scripts/agent-setup-admin.ps1` et `scripts/agent-setup.ps1`, repris des scripts
  de phase 0, en ASCII (Windows PowerShell 5.1 lit un fichier sans BOM en ANSI).
- Un verbe `agent` de `scripts/tessera.ps1` : `agent setup`, `agent jeton`
  (changer d'abonnement), `agent doctor`.
- `agent doctor` liste, avec son remède : compte présent, mot de passe et jeton
  dans le coffre, CLI partagé présent **et de la même version** que celui du SDK
  installé (après une montée du SDK, il faut le recopier), `uv` et `node`
  lisibles par l'agent.

## Critères d'acceptation

- [ ] `scripts/agent-setup-admin.ps1` existe, ne référence ni `$env:USERPROFILE`
      ni `$env:APPDATA`, et prend le nom du compte utilisateur en paramètre.
- [ ] `scripts/agent-setup.ps1` existe et refuse de tourner en administrateur.
- [ ] Les deux scripts ne contiennent que de l'ASCII ; un test pytest le vérifie
      sur `scripts/agent-setup*.ps1`.
- [ ] `scripts/tessera.ps1` accepte `agent` avec les sous-verbes `setup`, `jeton`
      et `doctor`, listés par `help`.
- [ ] `agent doctor` compare la version de `C:\ProgramData\Tessera\bin\claude.exe`
      et celle du CLI embarqué par le SDK, et dit comment recopier en cas d'écart.
- [ ] `docs/` contient une page qui décrit l'installation sur un nouveau poste,
      dont le cas d'un compte utilisateur non administrateur.

## Dépendances

ticket-894, dont le réglage `AGENT_USER` et les noms de secrets sont repris.

## Estimation

Un jour.

## Risques

Les scripts ne se testent pas en CI (création de compte). Les critères portent
sur ce qui se vérifie sans élévation ; la recette se fait à la main.

## Ce que ça ne fait pas

- Pas d'équivalent macOS ou Linux : un conteneur jouera ce rôle plus tard.