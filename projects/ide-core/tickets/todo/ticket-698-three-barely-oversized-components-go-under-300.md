---
id: ticket-698
title: "Three barely oversized components go under 300 lines"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: [ticket-681]
created: 2026-10-29
---

# ticket-698 — `FilDuRun`, `TicketCard` et `TicketList` sous 300 lignes

## Objectif
Retirer trois entrées du cliquet frontend qui dépassent de peu le plafond
général.

## Contexte
`components/FilDuRun/index.tsx` (360 : `formatDuree` et cinq vues de pas dans
le même fichier), `components/Sidebar/TicketCard.tsx` (314 : six tables de
styles et libellés, 17-68) et `components/Sidebar/TicketList.tsx` (309 :
composant de 237 lignes). Le ticket-681 sort `formatDuree` de `FilDuRun` ;
`docs/audit/refactos.md` §3.

## Critères d'acceptation
- [ ] Les vues `EntreeSecuriteView`, `EntreeValidateurView` et `EntreeTesteurView` vivent chacune hors de `FilDuRun/index.tsx` ; les tables de `TicketCard` vivent dans un fichier sans JSX
- [ ] Les trois entrées (`FilDuRun/index.tsx`, `Sidebar/TicketCard.tsx`, `Sidebar/TicketList.tsx`) disparaissent de `PLAFONDS`
- [ ] Les couleurs d'état restent dans `zinc`, `red`, `amber`, `green`, `blue` (ADR-026) : le test de palette existant passe
- [ ] `npm run test`, `npx tsc --noEmit` et `npm run lint` passent ; aucun test ne change d'attendu

## Ce que ça ne fait pas
- Ne change aucun rendu ni aucune classe Tailwind
- Ne touche pas à `ImportProjectModal` (ticket-697)
