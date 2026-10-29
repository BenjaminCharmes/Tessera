---
id: ticket-693
title: "API types split by domain"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-693 — `types/api.ts` découpé par domaine

## Objectif
Un fichier de types par domaine, plutôt qu'un fichier que chaque champ neuf
oblige à découper à la hâte.

## Contexte
`types/api.ts` (676 lignes) regroupe plus de soixante types : tickets, runs et
événements, projets, chat, usage et statistiques, agents, git et artefacts,
mise en ligne. Il a déjà dû être découpé le 28/10 pour un champ
(`types/apercuProjet.ts` en est un reste). `docs/audit/refactos.md` §1.

## Critères d'acceptation
- [ ] Aucun fichier de types ne dépasse 300 lignes ; l'entrée `types/api.ts` disparaît de `PLAFONDS` (`frontend/src/longueur-des-fichiers.test.ts`)
- [ ] Un type n'est défini qu'une fois : `grep -rn "export interface Ticket " frontend/src/types` ne rend qu'une ligne
- [ ] Soit les importeurs sont mis à jour, soit `types/api.ts` ne garde que des `export … from` ; dans les deux cas `npx tsc --noEmit` passe sans changement d'un seul type
- [ ] `npm run test`, `npx tsc --noEmit` et `npm run lint` passent ; aucun test ne change d'attendu

## Ce que ça ne fait pas
- Ne retype aucune réponse, ne confronte aucun type à son modèle (ticket-684)
- Ne touche pas aux types du dossier `bureau` (ticket-631)
