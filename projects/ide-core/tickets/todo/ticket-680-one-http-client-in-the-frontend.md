---
id: ticket-680
title: "One HTTP client in the frontend"
type: refactor
status: todo
priority: medium
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-680 — Un seul client HTTP côté frontend

## Objectif
Les lectures de `lib/` passent toutes par le même client (authentification,
erreur `API <code>: …`, décodage), au lieu de le recopier.

## Contexte
`request<T>` (`lib/api.ts:60`) est recopié dans `lib/quota.ts:19`,
`lib/statutDuRun.ts:21`, `lib/ventilation.ts:19`, `lib/capturesDuRun.ts:60`,
`lib/fs.ts:10,16,28,42` et partiellement `api.ts:94` (`docs/audit/doublons.md`
§2.1). La cause est le cliquet de longueur d'`api.ts` (ticket-545) : `request`
n'est pas exporté. Le même audit relève `StatutDuRun` sans `arretes` et un
`POST …/branches/cleanup` sans `Content-Type` (`api.ts:283`).

## Critères d'acceptation
- [ ] Le client vit dans son propre fichier (`lib/http.ts` ou équivalent) ; `api.ts`, `quota.ts`, `statutDuRun.ts`, `ventilation.ts`, `capturesDuRun.ts`, `fs.ts` l'importent
- [ ] `grep -rn "fetch(" frontend/src --include=*.ts --include=*.tsx` hors tests ne trouve plus que ce fichier
- [ ] `StatutDuRun` déclare `arretes: { ticket_id: string; motif: string | null }[]` ; un test lit une réponse avec `arretes` non vide
- [ ] `api.git.cleanup` envoie `Content-Type: application/json` ; un test vérifie l'en-tête
- [ ] Le cliquet de longueur d'`api.ts` n'est pas relevé (le test de cliquet passe sans modification de son plafond)
- [ ] `npm run test`, `npx tsc --noEmit` et `npm run lint` passent ; les tests existants des modules touchés passent sans modification de leurs attendus

## Ce que ça ne fait pas
- Ne retype aucune autre réponse (ticket-684)
- Ne change pas `useResource`
