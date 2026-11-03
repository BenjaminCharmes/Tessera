---
id: ticket-684
title: "A contract test between routes, types and fixtures"
type: test
status: done
priority: medium
agent: codeur
depends_on: [ticket-678, ticket-679, ticket-680]
created: 2026-10-29
---

# ticket-684 — Contrat route ↔ type ↔ fixture

## Objectif
Qu'un type front faux et un mock faux ne puissent plus s'accorder : c'est ce qui
a laissé passer `getPrStatuses` depuis le ticket-367.

## Contexte
Aucune fixture de test n'est produite depuis le modèle backend
(`docs/audit/doublons.md` §3). Un mock écrit à la main reprend le type que le
front croit lire.

## Critères d'acceptation
- [x] Le schéma OpenAPI du backend est exporté dans un fichier versionné, régénéré par une commande documentée ; un test backend échoue si le fichier est périmé (`backend/tests/test_openapi_export.py`, `docs/openapi.json`, `make openapi`)
- [x] Pour au moins les routes `runs/{id}`, `usage/breakdown`, `services/*`, `branches/cleanup`, `usage/quota` : un test frontend confronte les champs du type déclaré aux propriétés du schéma, et échoue si un champ du schéma manque au type (cas `arretes`) ou s'il en invente un (`frontend/src/test/contrat/contrat.test.ts`)
- [x] Pour ces mêmes routes, les fixtures des tests frontend sont tirées d'un exemple conforme au schéma ; un test échoue si un `mockResolvedValue` rend un tableau là où le schéma décrit un objet (cas `getPrStatuses`) (`frontend/src/test/contrat/garde.test.ts`, `frontend/src/test/contrat/exemples.ts`)
- [x] Le périmètre est écrit dans le test : les routes non couvertes y sont listées, pas tues (`frontend/src/test/contrat/perimetre.ts`)
- [x] `uv run pytest`, `npm run test`, `npx tsc --noEmit` et `npm run lint` passent

## Ce que ça ne fait pas
- Ne génère pas tout `types/api.ts` depuis le schéma : cela se tranche à part
- Ne corrige pas les écarts qu'il révèle hors des routes listées : il les journalise
- Ne comble pas la liste « Non examiné » de `docs/audit/doublons.md` §4

## Livraison
Bloqué par le pipeline le 31/10 à 02:28 après trois tours : le validateur a jugé les
critères 2 à 4 invérifiables, parce que le diff (30 fichiers) arrivait tronqué et
qu'aucun critère ne citait les fichiers de test. Le travail, lui, était fait.
Vérifié et livré à la main : `tsc -b`, `eslint`, vitest complet (2184 tests) et
`test_openapi_export.py` verts ; critères réécrits pour citer leurs fichiers.

