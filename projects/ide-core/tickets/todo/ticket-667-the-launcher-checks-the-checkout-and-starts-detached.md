---
id: ticket-667
title: "The launcher refuses a checkout off develop or behind origin, and starts the backend detached"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-29
---

# ticket-667 — Un lanceur qui vérifie le checkout et démarre détaché

## Objectif
Que `tessera.ps1 run` ne démarre jamais un backend sur le mauvais code, ni rattaché
à la console qui l'a lancé.

## Contexte
Piste reçue le 29/10 d'une session tierce (lanceur reprenant les vérifications du
skill `run-tessera`). `tessera.ps1 run` lance déjà `tessera.doctor`, qui contrôle les
ports 8100 et 5173 (`check_ports`). Mais deux pièges des redémarrages du 28/10
restent à la charge de la mémoire :
- le backend charge son code depuis le checkout, que les runs d'ide-core font
  changer de branche : démarré hors de `develop`, ou en retard sur `origin/develop`,
  il mélange les versions (`memory/redemarrer-le-backend`) ;
- `Start-Process` rattache le backend à la console qui le lance.

## Solution proposée
- `tessera.doctor` gagne `check_checkout` : la branche courante est `develop`, et
  `HEAD` égale `origin/develop` après un `fetch`. Sinon, le contrôle échoue en nommant
  la branche ou l'écart, avec la commande qui répare.
- `Start-Backend` (`scripts/tessera.ps1`) lance uvicorn par `Win32_Process.Create`
  (WMI), hors de la console appelante, et vérifie `/health`.

## Critères d'acceptation
- [ ] Un test de `tessera.doctor` vérifie que `check_checkout` échoue sur une branche autre que `develop`, en la nommant
- [ ] Un test vérifie que `check_checkout` échoue quand `HEAD` diffère de `origin/develop`, et réussit quand ils sont égaux
- [ ] `run_checks` inclut `check_checkout`
- [ ] `scripts/tessera.ps1` lance le backend par `Win32_Process` et attend `/health` avant de rendre la main

## Ce que ça ne fait pas
- Pas d'installeur Linux ni de tag de version automatique : un tag à chaque merge
  vers `main` passe par `.github/workflows/`, qu'aucun agent n'écrit (ADR-027). À faire à la main si Benjamin le veut.
