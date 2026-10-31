---
agent: codeur
created: 2026-10-29
depends_on:
- ticket-680
id: ticket-683
pr_number: 805
priority: low
status: done
title: A shared polling hook and clock
type: refactor
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

## Relevé des cinq boucles (première étape)

Ce que chaque hook refaisait à la main avant `usePolling` :

| Hook | Cadence | Visibilité (`useFenetreVisible`) | Condition d'activité | Appel immédiat + redémarrage | Arrêt depuis le rappel | Annulation d'une réponse en vol | Nettoyage |
|---|---|---|---|---|---|---|---|
| `usePrStatuses` | 30 s fixe | oui | projet, `clePr` non vide, PR non réglées | oui (au changement de projet, de `clePr`, au retour de visibilité) | oui (PR réglées, erreur 4xx) | drapeau `cancelled` | `clearInterval` via ref |
| `useRestants` | 30 s fixe | oui | `runId` et run non clos | non | non | portée par `useResource` | `clearInterval` |
| `useServices` | 5 s fixe | oui | projet et un service en cours | non | non | portée par `useResource` | `clearInterval` |
| `useTickets` | 30 s ou 60 s selon le pipeline | oui (plus une relance au retour) | projet | non | non | drapeau `cancelled` (effet de lecture) | `clearInterval` |
| `useAppsEnCours` | 10 s, ou 2 s si une opération est attendue | oui | aucune | non | non | drapeau `annule` (effet de lecture) | `clearInterval` |

`usePolling(rappel, { cadenceMs, immediat, relance })` couvre l'union :
cadence variable ou `null` (condition), visibilité, appel immédiat,
redémarrage par `relance`, arrêt par un état qui passe la cadence à `null`,
nettoyage. L'annulation d'une réponse en vol reste dans chaque hook, qui seul
connaît sa requête.

Pas de migration vers `useResource` : `usePrStatuses` s'arrête sur un état
réglé et sur une erreur 4xx, `useTickets` fusionne des événements WebSocket
dans sa liste, `useAppsEnCours` porte des opérations en attente. Son cache de
lecture changerait ces comportements. `useRestants` et `useServices` s'en
servent déjà, pour la lecture ; seul leur minuteur passe par `usePolling`.

`useMaintenant` garde son `setInterval` propre : une horloge ne se suspend pas
fenêtre cachée, et `Chrono.tsx` s'y branche (`useMaintenant(1000, !termineA)`).

## Vérification lancée

`vitest run src/hooks src/components` : 167 fichiers, 1491 tests verts, les
attendus des tests existants des cinq hooks inchangés. `tsc --noEmit -p
tsconfig.app.json` et `eslint src/hooks src/components/SupervisionView` sans
erreur.

## Ce que ça ne fait pas
- Ne migre pas ces hooks vers `useResource` si le tableau montre que son cache les gênerait : la PR le dit
- Ne touche pas `CompteARebours.tsx` ni `AgentDialogue.tsx` (horloges locales, non jugées)
- Ne touche pas `components/BureauView/` (ticket-631)