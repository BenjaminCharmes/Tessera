---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 1
id: ticket-264
plan: true
pr_number: 152
priority: high
status: done
title: In a queue, each ticket starts from the up-to-date remote base once the previous
  one merged
type: fix
---

# ticket-264 — Dans une file, un ticket repart de la base distante à jour

## Objectif

Qu'une file de tickets sur un projet en `autonomy: merge` merge chacun de ses
tickets, et pas seulement le premier.

## Contexte

Constaté le 2026-09-30 sur les files 253/254 et 259/260. Depuis le ticket-260,
la livraison merge une PR dont la CI est verte, en **squash** (la règle du
dépôt pour `ticket-XXX` → `develop`).

Mais dans une file :
- `GitWorkspaceService.create_branch` part de `_base_ref`, que
  `advance_base_ref` avance sur la branche du ticket approuvé : le ticket 2
  part donc de la branche du ticket 1, pas de `develop` ;
- `rebase_sur_la_base` (`services/git_workspace.py`) rebase sur la branche
  **locale** `develop`, sans `fetch`. La branche locale n'a jamais reçu le
  squash du ticket 1, fait côté GitHub.

La PR du ticket 2 porte donc les commits du ticket 1, déjà présents sur
`develop` sous forme d'un squash. GitHub la déclare en conflit — sur
`memory/pipeline-log.md` et le fichier du ticket 1, modifiés des deux côtés —
et le merge est refusé. Les deux fois, la branche a dû être réparée à la main.

## Solution proposée

À concevoir au tour de plan (`plan: true`). Piste attendue :

- Quand la livraison d'un ticket a **mergé** sa PR : `fetch` de la base
  distante, mise à jour de la branche locale de base (avance rapide seulement),
  et `_base_ref` repositionné sur elle. Le ticket suivant part alors de la base
  qui contient le squash.
- Quand la livraison **n'a pas mergé** (CI rouge, niveau `pr` ou `commit`) :
  comportement actuel inchangé — l'empilement reste ce qui permet à un plan
  séquentiel d'avancer (ADR-018).
- Aucun push forcé (ADR-022), aucune réécriture de la base locale autre qu'une
  avance rapide : si elle a divergé, on garde le comportement actuel et on le
  dit dans `Livraison.arret`.

## Critères d'acceptation

- [ ] Un test (dépôt git temporaire avec un faux distant) montre qu'après une
      livraison mergée, le ticket suivant de la file crée sa branche à partir du
      commit de la base distante mise à jour.
- [ ] Un test montre qu'après une livraison **non** mergée, le ticket suivant
      part toujours de la branche du ticket précédent.
- [ ] Un test montre qu'une base locale divergente de la base distante n'est
      pas réécrite, et que la raison apparaît dans `Livraison.arret`.
- [ ] Le diff n'ajoute aucun `push --force` ni `reset --hard`.

## Dépendances

Aucune.

## Estimation

1 jour. Backend uniquement.

## Risques

- Ne pas confondre avec ADR-033 : la mise à jour se fait **entre** deux
  tickets, jamais pendant un rebase en cours.
- Le fetch est un appel réseau : il ne part que sur un projet qui a un distant
  lié et un niveau `merge`.