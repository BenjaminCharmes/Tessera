---
id: ticket-529
title: "The three worktree rules are accepted and reach the agents"
type: chore
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-519", "ticket-520", "ticket-523"]
estimated_days: 0.1
created: 2026-10-22
---

# ticket-529 — Les trois règles du worktree sont acceptées

## Objectif
Faire passer les trois règles d'ADR-056 de `## Proposées` à leur section dans
`memory/contraintes.md`, pour qu'elles partent dans les appels d'agents.

## Contexte
Les tickets 519 à 525 et 520 ont livré le worktree par run ; ils sont actifs
depuis le redémarrage du 20/10. Les trois règles attendaient sous
`## Proposées`, une section qu'aucun agent ne reçoit (ADR-055). Le passage en
worktree d'un projet se décide ensuite projet par projet dans `agents.json` :
accepter les règles n'active rien seul.

Décision déléguée par Benjamin le 22/10 (« prends la décision que tu
recommandes »).

## Solution proposée
À la main : un run qui écrit hors de `## Proposées` est mis en `blocked`
(ADR-055).
- racine d'écriture et liens de `populate` → `## Git et périmètre d'écriture` ;
- worktree non commité jamais supprimé → `## Portes qui échouent fermées`,
  à côté de la règle ADR-037 dont elle découle.

## Critères d'acceptation
- [x] `memory/contraintes.md` ne porte plus aucune règle sous `## Proposées`
- [x] Les deux règles d'écriture sont sous `## Git et périmètre d'écriture`
- [x] La règle du worktree non commité est sous `## Portes qui échouent fermées`
- [x] `test_contraintes_proposees.py`, `test_consignes_coherentes.py` et
      `test_adr_pertinents.py` passent

## Ce que ça ne fait pas
- Ne déclare `worktree` dans l'`agents.json` d'aucun projet.
