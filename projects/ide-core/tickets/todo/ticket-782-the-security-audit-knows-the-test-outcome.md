---
id: ticket-782
title: "The security audit knows the test outcome of its round"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-782 — L'audit sécurité connaît le résultat des tests de son tour

## Objectif

L'audit sécurité ne bloque plus un run en affirmant un échec que les tests du même tour
viennent de démentir.

## Contexte

04/11, ticket-750 : le testeur rend la suite verte à 09:58:49 ; l'audit sécurité, lancé à la
seconde suivante, rend `BLOCK` avec une faille `CRITICAL` : « l'indexage `[0]` cause une
ValueError (…) Tous les tests sur cp/mv/rm échouent immédiatement ». C'était faux (lecture
erronée d'un déballage de tuple) ; une faille `CRITICAL` bloque quel que soit le verdict
(ADR-039), la file s'est interrompue et le ticket a été fini à la main (#873).

`run_security_audit` (`backend/src/tessera/services/pipeline_controles.py`) passe à l'auditeur
le diff et un `AuditContext` (`backend/src/tessera/services/security_contexte.py` : section
« ne fait pas », tickets suivants), mais pas `run.test_result`, que le validateur reçoit déjà.

## Solution proposée

- `AuditContext` porte le résultat des tests du tour quand le testeur a tourné : vert ou rouge,
  le résumé, et les échecs nommés.
- Le message de l'auditeur l'énonce comme un fait (« Les tests de ce tour sont verts : … »), et
  son prompt dit qu'une faille qui affirme un échec à l'exécution doit s'accorder avec ce
  résultat.
- Sans testeur actif, rien n'est ajouté.

## Critères d'acceptation

- [ ] Un test vérifie que `build_audit_context` (ou son appelant) porte le résultat des tests
      quand `run.test_result` existe, et rien quand il n'existe pas
- [ ] Un test vérifie que le message envoyé à l'auditeur contient le résumé des tests verts du
      tour
- [ ] Un test vérifie que des tests rouges y figurent avec les noms des tests en échec
- [ ] `agents/prompts/securite.md` dit qu'une faille affirmant un échec à l'exécution doit
      s'accorder avec le résultat des tests fourni

## Ce que ça ne fait pas

Ne rétrograde aucune faille automatiquement : la règle d'ADR-039 (une `CRITICAL` bloque)
reste entière ; l'auditeur dispose seulement du fait qui lui manquait.
