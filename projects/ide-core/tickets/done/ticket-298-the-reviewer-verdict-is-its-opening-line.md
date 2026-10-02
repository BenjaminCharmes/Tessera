---
id: ticket-298
title: "The reviewer's verdict is the line it opens with, not any mention of CHANGES_REQUESTED"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-01
---

# ticket-298 — Le verdict du reviewer est la ligne qui l'ouvre

## Objectif

Qu'une approbation qui cite `CHANGES_REQUESTED` dans son corps soit lue comme
une approbation.

## Contexte

Le 2026-10-01, le ticket-288 s'est bloqué après trois tours. Le reviewer avait
répondu `APPROVED` les trois fois, en tête de réponse, comme son prompt le
demande. Mais `_parse_reviewer_verdict` (`services/pipeline_text.py`) donnait
la priorité à `CHANGES_REQUESTED` **où qu'il apparaisse** (ADR-009). Or le
ticket-288 corrige justement le motif des refus, et le reviewer écrivait
« Bug `CHANGES_REQUESTED` réellement corrigé ». Les trois approbations ont
donc été lues comme trois refus, et chacun renvoyait au codeur une
approbation en guise de motif.

Fait à la main : ce correctif ne peut pas passer par le pipeline, dont le
reviewer citerait le mot dans son avis et ferait refuser le run par le défaut
même qu'il corrige.

## Solution

- Le verdict est la première ligne qui **commence** par `APPROVED` ou
  `CHANGES_REQUESTED`, une fois retirée la mise en forme Markdown (`**`, `#`,
  `` ` ``). C'est le format imposé par `agents/prompts/reviewer.md`.
- Une telle ligne qui commence par `APPROVED` mais nomme `CHANGES_REQUESTED`
  refuse.
- Sans ligne de verdict, la règle d'avant s'applique : `CHANGES_REQUESTED`
  n'importe où l'emporte, et une réponse sans verdict refuse (ADR-039).
- ADR-009 est amendé.

## Critères d'acceptation

- [x] Un test vérifie qu'une approbation qui cite `CHANGES_REQUESTED` dans son
      corps approuve
- [x] Un test vérifie qu'une ligne de prose avant `**APPROVED**` ne change
      pas le verdict
- [x] Un test vérifie qu'un `## CHANGES_REQUESTED: motif` en tête refuse et
      garde son motif
- [x] Les tests existants du parseur (tickets 122 et ADR-009) passent

## Ce que ça ne fait pas

Le résumé du reviewer dans la vue du run (`FilDuRun.resumePassage`) a le même
défaut côté frontend : le ticket-282, qui réécrit cet en-tête, doit le
reprendre.
