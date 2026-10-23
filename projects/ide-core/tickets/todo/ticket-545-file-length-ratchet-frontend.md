---
id: ticket-545
title: "A frontend file can no longer grow past its ceiling"
type: test
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-23
---

# ticket-545 — Un cliquet sur la longueur des fichiers frontend

## Objectif
Même règle que le ticket-544 côté frontend : 300 lignes au plus pour un
fichier nouveau, la taille actuelle comme maximum pour ceux qui dépassent.

## Contexte
Hors tests, 24 fichiers de `frontend/src` dépassent 200 lignes, dont
`hooks/streamState.ts` (716), `types/api.ts` (710) et `hooks/useCockpit.ts`
(537). ESLint est déjà dans la `test_command` (`scripts/verifier.py`).

## Solution proposée
Un test vitest, sur le modèle du ticket-544, plutôt qu'une règle ESLint
`max-lines` : la règle ESLint ne sait pas faire un cliquet, et une exception
par fichier dans `eslint.config.js` se relève sans que personne le voie. Les
fichiers `*.test.ts(x)` sont exclus.

## Critères d'acceptation
- [ ] `frontend/src/longueur-des-fichiers.test.ts` existe et définit le plafond général à 300 lignes
- [ ] Sa table `PLAFONDS` liste chaque fichier `.ts`/`.tsx` non test de `frontend/src` qui dépasse 300 lignes au moment du ticket, avec sa taille exacte
- [ ] La logique de contrôle est une fonction pure testée : un fichier hors table de 301 lignes échoue, un fichier de la table au-dessus de son maximum échoue, un fichier de la table passé sous son maximum échoue avec un message qui demande de baisser le plafond
- [ ] Le diff ne modifie pas `frontend/eslint.config.js`

## Ce que ça ne fait pas
- Ne découpe aucun composant.
