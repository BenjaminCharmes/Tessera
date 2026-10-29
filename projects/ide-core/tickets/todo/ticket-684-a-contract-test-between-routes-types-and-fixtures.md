---
id: ticket-684
title: "A contract test between routes, types and fixtures"
type: test
status: todo
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
- [ ] Le schéma OpenAPI du backend est exporté dans un fichier versionné, régénéré par une commande documentée ; un test backend échoue si le fichier est périmé
- [ ] Pour au moins les routes `runs/{id}`, `usage/breakdown`, `services/*`, `branches/cleanup`, `usage/quota` : un test frontend confronte les champs du type déclaré aux propriétés du schéma, et échoue si un champ du schéma manque au type (cas `arretes`) ou s'il en invente un
- [ ] Pour ces mêmes routes, les fixtures des tests frontend sont tirées d'un exemple conforme au schéma ; un test échoue si un `mockResolvedValue` rend un tableau là où le schéma décrit un objet (cas `getPrStatuses`)
- [ ] Le périmètre est écrit dans le test : les routes non couvertes y sont listées, pas tues
- [ ] `uv run pytest`, `npm run test`, `npx tsc --noEmit` et `npm run lint` passent

## Ce que ça ne fait pas
- Ne génère pas tout `types/api.ts` depuis le schéma : cela se tranche à part
- Ne corrige pas les écarts qu'il révèle hors des routes listées : il les journalise
- Ne comble pas la liste « Non examiné » de `docs/audit/doublons.md` §4
