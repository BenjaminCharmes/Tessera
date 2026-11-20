---
agent: codeur
created: 2026-11-13
depends_on: []
id: ticket-966
priority: medium
status: done
title: "A vitest setup file counts as test configuration, as contraintes.md says"
type: fix
---

# ticket-966 — Un fichier de setup vitest compte comme configuration des tests

## Contexte

Signalement de la session Kadoomi (13/11, ticket-178, run 3ee5bed0) : le
diff ajoutait un polyfill dans `vitest.setup.ts`, que le ticket ne nommait
pas. La porte ADR-072 ne l'a pas vu : `contraintes.md` dit `vitest.*`, mais
`NOMS_SIGNALES` (`services/gardes/config_tests_touchee.py`) ne portait que
`vitest.config.*` et `vitest.workspace.*`. Un setup global peut pourtant
affaiblir tous les tests (mock d'une erreur, assertion neutralisée).

## Correctif

`NOMS_SIGNALES` porte `vitest.*`, comme la règle.

## Critères d'acceptation

- [x] Un test : un diff de `frontend/vitest.setup.ts` est reconnu comme
      configuration des tests.
- [x] Les tests existants de la porte passent sans changement.

## Ce que ça ne fait pas

- Ne suit pas les fichiers que `setupFiles` nomme sous un autre nom
  (`src/setupTests.ts`) : à voir si un cas réel se présente.
- Fait à la main : un motif de la liste.
