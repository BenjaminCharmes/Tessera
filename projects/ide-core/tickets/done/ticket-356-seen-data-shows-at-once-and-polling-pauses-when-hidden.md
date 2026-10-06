---
agent: codeur
created: 2026-10-05
depends_on: []
estimated_days: 1
id: ticket-356
pr_number: null
priority: medium
status: done
title: Data already seen shows at once while it refreshes, and polling pauses while
  the window is hidden
type: fix
---

# ticket-356 — Une donnée déjà vue s'affiche aussitôt, et le polling s'arrête fenêtre cachée

## Objectif

Que revenir sur un projet ou un ticket déjà ouvert affiche immédiatement ce
qu'on avait vu, rafraîchi en fond, et que l'application cesse d'interroger le
serveur quand personne ne la regarde.

## Contexte

`useResource` (`frontend/src/hooks/useResource.ts`) n'a pas de cache : au
changement de `fetcher`, il repasse à `initial` et affiche un chargement, même
pour une donnée vue il y a une seconde.

Le polling ne tient jamais compte de la visibilité de la fenêtre :
- `useTickets` (`frontend/src/hooks/useTickets.ts`) recharge toute la liste
  toutes les 30 s pendant une file, 60 s sinon ;
- chaque `TicketCard` qui a une PR (`frontend/src/components/Sidebar/TicketCard.tsx`)
  interroge `/pr-status` toutes les ~30 s, et dès son montage ;
- `useServices` (`frontend/src/hooks/useServices.ts`) toutes les
  `CADENCE_MS`.

`document.visibilityState` n'est lu que pour les notifications
(`useNotificationsSysteme.ts`).

## Solution proposée

1. `useResource(fetcher, initial, cle?)` : avec une `cle` (chaîne), la
   dernière donnée obtenue pour cette clé est gardée dans un cache de niveau
   module (borné, 100 entrées, plus ancienne évincée) et rendue **aussitôt**
   au changement de `fetcher`, avec `loading: true` le temps du
   rafraîchissement. Sans `cle`, le comportement actuel est inchangé. Une
   donnée d'un autre projet ne s'affiche jamais : la clé inclut l'id du
   projet.
2. Passer une `cle` aux appels qui chargent le ticket ouvert et la liste des
   tickets.
3. Un hook `useFenetreVisible()` (`frontend/src/hooks/useFenetreVisible.ts`)
   basé sur `visibilitychange`. `useTickets`, `useServices` et le polling de
   `TicketCard` suspendent leur intervalle fenêtre cachée, et relancent une
   requête immédiate au retour.

## Critères d'acceptation

- [ ] Un test de `useResource.test.ts` montre qu'en revenant à une clé déjà
      chargée, la donnée précédente est rendue avant la fin de la nouvelle
      requête, avec `loading` vrai
- [ ] Un test de `useResource.test.ts` montre que sans `cle`, le changement
      de `fetcher` rend toujours `initial`
- [ ] `useFenetreVisible.ts` existe, avec un test qui simule
      `visibilitychange`
- [ ] Un test de `useTickets.test.ts` montre qu'aucune requête n'est faite
      pendant que la fenêtre est cachée, et qu'une requête part à son retour
- [ ] Un test de `TicketCard.test.tsx` montre que le polling de statut de PR
      s'arrête fenêtre cachée

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

Une donnée en cache périmée s'affiche un instant : c'est voulu, le
rafraîchissement suit aussitôt et `loading` le signale.