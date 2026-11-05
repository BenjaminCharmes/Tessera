---
id: ticket-769
title: "Service journal lines are classified and numbered truthfully"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-769 — Les lignes du journal d'un service sont classées et numérotées sans mentir

## Objectif

Le journal en ligne d'une salle serveur ne rougit pas une ligne saine, et ses numéros ne
glissent pas sous les yeux.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-710.
- `frontend/src/components/EnCoursView/journal.ts` classe en erreur toute ligne contenant
  `error` : « ✓ built, 0 error » passe en rouge, compte dans « Erreurs · N » et peut rougir
  l'écran mural (vérifié).
- `JournalDuService.tsx` numérote par rang dans le tampon de 200 lignes du backend : une fois
  le tampon plein, chaque relecture décale les numéros.

## Critères d'acceptation

- [x] Un test vérifie que « ✓ built, 0 error » et « 0 errors » ne sont pas des erreurs, et que
      « Error: boom » en est une
- [x] Le backend rend, avec le tampon, le nombre de lignes écartées en tête, et un test
      vérifie que le numéro d'une même ligne ne change pas entre deux relectures quand le
      tampon déborde
