---
id: ticket-736
title: "A queue skips a ticket already finished on the base branch"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-736 — Une file saute un ticket déjà terminé sur la branche de base

## Objectif

Une file ne rejoue jamais un ticket déjà `done` ou `cancelled` sur `origin/<base>`,
même quand l'arbre de travail du projet le montre encore en `todo`.

## Contexte

02/11, 18:55 : une file ide-core est lancée alors que le checkout est resté sur la
branche du ticket-700, partie de `develop` **avant** le merge du ticket-699 (#832).
Dans cet arbre, 699 est encore dans `todo/`. La file le reprend
(`run_resumed_from_existing_work` sur sa vieille branche), relance les tests, et le
testeur reste figé jusqu'au lendemain 07:48 : une nuit perdue, la file interrompue
avant d'avoir touché aux six tickets suivants.

La garde existe : `_deja_termine` (`backend/src/tessera/services/pipeline_file.py`)
saute un ticket terminé (ticket-115). Mais elle s'appuie sur
`Orchestrator._est_termine` (`backend/src/tessera/services/orchestrator.py`), qui ne
lit que l'arbre de travail — périmé dans ce cas. La lecture de la base sans toucher
l'arbre existe déjà : `lire_ticket_sur_la_base`
(`backend/src/tessera/services/git_workspace/ticket_sur_base.py`, ticket-504).

## Solution proposée

- `_est_termine` reste vrai pour un ticket terminé dans l'arbre. Sinon, quand
  l'orchestrateur a un `GitWorkspaceService`, il lit le ticket sur `origin/<base>`
  par `lire_ticket_sur_la_base` et le juge terminé si son `status` y est `done` ou
  `cancelled`.
- Lecture impossible (fetch en échec, ticket absent de la base, frontmatter
  illisible) : on garde le verdict de l'arbre, sans bloquer la file.
- Le journal dit pourquoi le ticket est sauté : « déjà terminé sur la base ».

## Critères d'acceptation

- [ ] Un test vérifie, avec des doubles, qu'un ticket `todo` dans l'arbre mais `done`
      sur la base est jugé terminé par `_est_termine`
- [ ] Un test vérifie qu'un ticket `cancelled` sur la base est aussi jugé terminé
- [ ] Un test vérifie que, quand `lire_ticket_sur_la_base` renvoie None, `_est_termine`
      garde le verdict de l'arbre (`todo` → non terminé)
- [ ] Un test vérifie qu'un ticket terminé dans l'arbre est jugé terminé sans appeler
      `lire_ticket_sur_la_base`
- [ ] Un ticket sauté parce qu'il est terminé sur la base laisse dans le journal une
      ligne qui contient « déjà terminé sur la base »

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

- Un `fetch` par ticket de la file : acceptable (une fois par tour, déjà le cas de
  l'ajout), mais ne pas le refaire pour chaque appel dans un même tour.
