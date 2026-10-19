---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 0.5
id: ticket-508
pr_number: 549
priority: high
status: done
title: Appending a ticket merged on the base works when the project declares no base_branch
type: fix
---

# ticket-508 — L'ajout d'un ticket mergé marche aussi sans `base_branch` déclaré

## Objectif
Qu'un ticket mergé sur la base pendant une file puisse être ajouté à cette
file même quand le projet ne déclare pas `base_branch`, ce qui est le cas
d'ide-core.

## Contexte
Le ticket-504 a ajouté `GitWorkspaceService.lire_ticket_sur_la_base`
(`backend/src/tessera/services/git_workspace.py`), utilisé par
`POST /orchestrator/runs/{run_id}/append`. Il lit
`self._politique.base_branch` et renvoie `None` si elle est vide. Or
`projects/ide-core/agents.json` ne déclare pas `base_branch` : la livraison
retombe alors sur `settings.github_base_branch` (« develop »,
`backend/src/tessera/config.py`), mais ce lecteur, lui, abandonne.

Le 19/10 à 09:50 UTC, avec le 504 actif, l'ajout de ticket-507 (mergé sur
`origin/develop`, PR #543) à la file ide-core a répondu
`{"refuses": {"ticket-507": "ticket introuvable"}}`. Un appel direct à
`lire_ticket_sur_la_base("ticket-507")` sur ide-core renvoie `None`, avec
`base_branch` à `None`.

## Solution proposée
Quand la politique ne déclare pas de base, `lire_ticket_sur_la_base` utilise
la même base que la livraison : `settings.github_base_branch`. La règle de
repli est écrite une seule fois, de préférence dans une petite fonction que
la livraison et ce lecteur partagent, si la livraison en a déjà une.

## Critères d'acceptation
- [ ] Dans `git_workspace.py`, `lire_ticket_sur_la_base` lit le ticket sur `origin/<settings.github_base_branch>` quand `politique.base_branch` est `None`
- [ ] Un test dans `backend/tests/test_ajout_ticket_sur_la_base.py` couvre un dépôt dont la politique ne déclare pas de base : un ticket présent seulement sur `origin/develop` est retrouvé
- [ ] Un test vérifie qu'une `base_branch` déclarée garde la priorité sur `settings.github_base_branch`
- [ ] Les tests existants de `test_ajout_ticket_sur_la_base.py` passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
Aucun écrit : le lecteur reste en lecture seule (`fetch --no-write-fetch-head`,
`ls-tree`, `show`).