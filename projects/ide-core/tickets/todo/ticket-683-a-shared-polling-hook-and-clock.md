---
id: ticket-683
title: "A shared polling hook and clock"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: [ticket-680]
created: 2026-10-29
---

# ticket-683 — Un hook de polling et une horloge partagés

## Objectif
Les cinq boucles `setInterval` de lecture périodique passent par un hook
commun ; `Chrono.tsx` réutilise `useMaintenant`.

## Contexte
`docs/audit/doublons.md` §2.3 : `usePrStatuses.ts:91`, `useRestants.ts:45`,
`useServices.ts:174`, `useTickets.ts:95`, `useAppsEnCours.ts:111`.
`SupervisionView/Chrono.tsx:29` refait `hooks/useMaintenant.ts:8`. L'audit n'a
pas établi si chaque boucle réécrit aussi l'annulation et `useFenetreVisible`.

## Critères d'acceptation
- [ ] **Première étape, dans la PR :** un tableau relève, pour les cinq hooks, ce que chacun refait à la main (annulation, visibilité, cadence, nettoyage) ; le hook commun couvre l'union
- [ ] Un hook `usePolling` (cadence, visibilité de la fenêtre, annulation) remplace les cinq `setInterval`
- [ ] `Chrono.tsx` appelle `useMaintenant` ; `grep -n "setInterval" frontend/src/components/SupervisionView/Chrono.tsx` ne rend rien
- [ ] Un test du hook couvre : tick, fenêtre masquée, démontage sans fuite
- [ ] Les tests existants des cinq hooks passent sans modification de leurs attendus
- [ ] `npm run test`, `npx tsc --noEmit` et `npm run lint` passent

## Ce que ça ne fait pas
- Ne migre pas ces hooks vers `useResource` si le tableau montre que son cache les gênerait : la PR le dit
- Ne touche pas `CompteARebours.tsx` ni `AgentDialogue.tsx` (horloges locales, non jugées)
- Ne touche pas `components/BureauView/` (ticket-631)
