---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 0.5
id: ticket-259
pr_number: null
priority: high
status: done
title: Pull requests opened by delivery carry the ticket type prefix in their title
type: fix
---

# ticket-259 — Le titre d'une PR ouverte par la livraison porte le type du ticket

## Objectif

Qu'une PR ouverte par l'IDE ait un titre Conventional Commits, comme le commit
qu'elle porte.

## Contexte

Constaté sur la PR #130 (ticket-253) : titre `ticket-253 — Stats column…`, sans
préfixe. `CLAUDE.md` et ADR-044 exigent des titres de PR en Conventional
Commits, et la PR de ticket se merge en **squash** : son titre devient le
message du commit sur `develop`. Chaque PR ouverte par la livraison écrit donc
un commit non conforme dans l'historique.

Le commit du run, lui, est conforme : `pipeline_outcomes.py` le construit en
`f"{run.ticket.type.value}: {run.ticket_id} — {titre}"`. Le titre de PR est
construit ailleurs, dans `GitHubWorkflowService.open_pull_request`
(`services/github_workflow.py`) : `title=f"{ticket_id} — {ticket_title}"`. Le
type du ticket n'y parvient pas — `LivraisonService` (`services/livraison.py`)
ne transmet que l'id, le titre et le corps.

## Solution proposée

- Ajouter un paramètre `ticket_type: str` à `open_pull_request`, et construire
  le titre en `f"{ticket_type}: {ticket_id} — {ticket_title}"` — la même forme
  que le message de commit.
- Le faire transmettre par `LivraisonService` et par tout autre appelant de
  `open_pull_request` (routeur compris), depuis `ticket.type.value`.
- Ne pas dupliquer la mise en forme : si une fonction de `pipeline_outcomes.py`
  la porte déjà, la réutiliser plutôt que de réécrire le f-string.

## Critères d'acceptation

- [ ] `open_pull_request` accepte un paramètre `ticket_type`.
- [ ] Un test montre qu'un ticket de type `feat` ouvre une PR intitulée
      `feat: ticket-XXX — <titre>` (appel à `create_pull_request` vérifié sur
      un faux client GitHub).
- [ ] Un test montre que `LivraisonService` transmet le type du ticket à
      `open_pull_request`.
- [ ] Chaque appelant de `open_pull_request` dans `backend/src/` passe
      `ticket_type`.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Backend uniquement.

## Risques

- Un titre de ticket qui commence déjà par un type (`feat: …`) donnerait
  `feat: ticket-XXX — feat: …`. Le frontmatter `title` n'en porte pas par
  convention ; ne pas ajouter de logique de dédoublonnage.