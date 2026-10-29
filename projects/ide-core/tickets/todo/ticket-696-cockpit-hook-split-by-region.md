---
id: ticket-696
title: "Cockpit hook split by region"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-696 — `useCockpit` découpé par région

## Objectif
Le hook de composition (ticket-252) se compose lui-même de hooks par région de
l'écran, chacun rendant son groupe de props.

## Contexte
`hooks/useCockpit.ts` (532 lignes) : un seul hook de ≈ 421 lignes qui assemble
une vingtaine de hooks (`useSupervision`, `useRunActif`, `useServices`,
`useAppsEnCours`, `useNotificationsSysteme`…) et rend des groupes par région.
C'est un compositeur voulu ; la longueur vient du nombre de groupes, pas d'un
mélange de logique. `docs/audit/refactos.md` §1.

## Critères d'acceptation
- [ ] Un hook par région (colonne latérale, centre, panneau d'agent, notifications) dans des fichiers de moins de 300 lignes ; `useCockpit` ne fait que les appeler et rendre l'objet
- [ ] Le type de retour de `useCockpit` est inchangé : `npx tsc --noEmit` passe sans modifier `App.tsx`
- [ ] L'entrée `hooks/useCockpit.ts` de `PLAFONDS` est baissée d'au moins 150 lignes, ou retirée
- [ ] Pas de store global (ADR-013) : `grep -rn "zustand\|jotai" frontend/src` ne rend rien
- [ ] `npm run test`, `npx tsc --noEmit` et `npm run lint` passent ; les tests existants de `useCockpit` ne changent pas d'attendu

## Ce que ça ne fait pas
- Ne réévalue pas ADR-013 : si les groupes ne suffisent plus, c'est un ADR à part
- Ne change aucun comportement persistant (`useEtatPersistant`, `useProjetMemorise`)
