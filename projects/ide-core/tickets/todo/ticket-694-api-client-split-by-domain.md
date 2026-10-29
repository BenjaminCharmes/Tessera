---
id: ticket-694
title: "API client split by domain"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: [ticket-680]
created: 2026-10-29
---

# ticket-694 — `lib/api.ts` découpé par domaine

## Objectif
L'objet `api` se compose de modules par domaine qui importent le client de
`lib/http.ts`, sans changer un seul appel côté composant.

## Contexte
`lib/api.ts` (334 lignes) : helpers HTTP (58-100) et un objet `api` de 231
lignes pour tous les domaines. Le ticket-680 extrait le client dans
`lib/http.ts` ; après lui, ce fichier n'a plus de raison de rester d'un bloc.
Le §2.1 de `doublons.md` attribuait la copie du client au cliquet : 680 la
règle seul, cette découpe n'est pas un préalable.

## Critères d'acceptation
- [ ] `api.tickets.…`, `api.git.…`, `api.services.…` restent appelables sous les mêmes noms : `npx tsc --noEmit` passe sans modifier un composant
- [ ] Aucun module de domaine ne dépasse 300 lignes ; l'entrée `lib/api.ts` disparaît de `PLAFONDS`
- [ ] `grep -rn "fetch(" frontend/src --include=*.ts --include=*.tsx` hors tests ne trouve toujours que `lib/http.ts`
- [ ] `npm run test`, `npx tsc --noEmit` et `npm run lint` passent ; les tests existants de `lib/` ne changent pas d'attendu

## Ce que ça ne fait pas
- Ne change aucune URL, aucun en-tête, aucun type de réponse
