---
id: ticket-789
title: "CI watcher log lines never leave the base checkout dirty"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-786"]
estimated_days: 1
created: 2026-11-04
---

# ticket-789 — Les lignes de journal de CIWatcher ne salissent jamais le checkout de base

## Objectif

Après un merge fait par CIWatcher, l'arbre du checkout reste propre sur la branche de base
(ADR-018, ADR-037).

## Contexte

04/11, portfolio, run 3fba3df7 : PR #27 mergée par CIWatcher. Le checkout sur `main` porte deux
lignes non commitées dans `memory/pipeline-log.md` : « PR #27 confiée au CIWatcher » et « PR #27
mergée (CI verte) ». Le même jour, Kadoomi, Devinoo, Curio et Habit Tracker montraient tous ce
fichier modifié dans leur checkout.

`ajouter_au_log` (`backend/src/tessera/services/journal_ci_watcher.py`) ajoute la ligne
directement au journal du checkout. CIWatcher tourne en fond (phase 2, ADR-051), après le
retour du checkout sur la base : la ligne atterrit dans un fichier suivi, sur la base, sans
commit. Le ticket-786 met de côté, hors du dépôt, les lignes écrites après la fermeture d'une
file, et les réécrit dans la branche du run suivant : CIWatcher écrit souvent plus tard encore,
quand aucune file n'est ouverte.

## Solution proposée

- Quand le journal du projet est suivi par git, `ajouter_au_log` écrit la ligne dans le fichier
  d'attente hors dépôt du ticket-786 au lieu du journal du checkout ; le run suivant la réécrit
  dans sa branche avec les autres lignes en attente.
- Journal non suivi (artefacts `local`, ADR-021/023) : comportement actuel, la ligne s'ajoute au
  journal.
- `ajouter_au_log` ne lève toujours jamais.

## Critères d'acceptation

- [ ] Un test vérifie, sur un dépôt git temporaire dont le journal est suivi, qu'après
      `ajouter_au_log` `git status --porcelain` est vide et la ligne figure dans le fichier
      d'attente
- [ ] Un test vérifie qu'avec un journal non suivi la ligne est ajoutée au journal, comme avant
- [ ] Un test vérifie qu'une ligne mise en attente par CIWatcher est réécrite dans le journal de
      la branche du run suivant
