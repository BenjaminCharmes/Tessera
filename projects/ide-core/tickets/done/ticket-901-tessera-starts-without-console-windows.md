---
id: ticket-901
title: "Tessera starts without opening console windows"
type: chore
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-10
---

# ticket-901 — Tessera démarre sans ouvrir de fenêtres de console

## Objectif

`.\scripts\tessera.ps1 run` démarre le backend et Vite sans ouvrir de fenêtre
de console. Leur sortie va dans un fichier de journal.

## Contexte

`Start-Backend` lance uvicorn par `Win32_Process.Create` : le backend survit à
la console qui le lance (ticket-667), mais Windows lui ouvre une fenêtre.
`Start-Frontend` passe par `Start-Process npm.cmd`, qui en ouvre une autre.
Deux terminaux restent ouverts à chaque lancement. Les services des projets,
lancés par le backend, n'en ouvrent aucun : c'est ce qu'attend l'utilisateur.

## Solution proposée

- Une fonction `Start-Cache` : `Win32_Process.Create` avec une instance
  `Win32_ProcessStartup` dont `ShowWindow = 0` (fenêtre masquée). La commande
  passe par `cmd /c "… > journal 2>&1"` pour garder la sortie.
- Journaux dans `%LOCALAPPDATA%\Tessera\logs\` (`backend-console.log`,
  `vite.log`), hors du dépôt, écrasés à chaque lancement. Le chemin est affiché
  à la fin de `run`.
- `Start-Backend` et `Start-Frontend` passent par `Start-Cache`. `Wait-Health`
  ne change pas. En cas d'échec, son message cite le journal du backend.
- `tessera.ps1 stop` arrête toujours les deux, car il cible les ports et les
  lignes de commande, pas les fenêtres.

## Critères d'acceptation

- [ ] `scripts/tessera.ps1` définit `Start-Cache`, qui passe à
      `Win32_Process.Create` un `ProcessStartupInformation` avec
      `ShowWindow = 0`
- [ ] `Start-Frontend` n'appelle plus `Start-Process`
- [ ] Un test de `backend/tests/` vérifie ces deux points sur le texte du
      script, et que les journaux vont sous `LOCALAPPDATA`
- [ ] Le script s'analyse sans erreur avec le parseur PowerShell

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Sans fenêtre, une erreur de démarrage ne se voit plus à l'écran : elle est
dans le journal, dont le chemin est affiché.
