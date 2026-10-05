---
agent: codeur
created: 2026-10-05
depends_on: []
estimated_days: 0.5
id: ticket-344
pr_number: null
priority: medium
status: done
title: Supervision closes finished runs in bulk, by outcome
type: feat
---

# ticket-344 — Fermer les runs clos par lot, selon leur issue

## Objectif

Que l'onglet Supervision se vide en un clic des runs terminés, bloqués ou en
erreur, au lieu d'une carte à la fois.

## Contexte

Depuis le ticket-267, `run_closed` marque un run clos (`runClosed: true`)
sans le retirer : la carte reste jusqu'au bouton « Fermer » de l'`AgentPanel`
(`frontend/src/components/AgentPanel/index.tsx`), qui appelle
`fermerRun(runId)` de `frontend/src/hooks/useSupervision.ts`. Un run à la
fois, et il faut d'abord le sélectionner.

Après une file ou une journée de runs sur plusieurs projets, la colonne de
cartes s'allonge sans fin : rien ne permet de la nettoyer d'un geste, ni de
garder les bloqués à l'écran pendant qu'on écarte ce qui est livré.

La fermeture reste purement frontend : le backend a déjà retiré le run de
`RunRegistry` à sa clôture (`backend/src/tessera/services/run_registry.py`,
`fermer`). Rien à changer côté serveur.

## Solution proposée

1. **Une fonction pure** `issueDuRun(etat: StreamState)` dans un nouveau
   fichier `frontend/src/components/SupervisionView/issueDuRun.ts`, qui rend
   `"en-cours" | "termine" | "bloque" | "erreur" | "autre"` :
   - `"en-cours"` tant que `etat.runClosed` est faux — quelle que soit le
     reste de l'état ;
   - `"erreur"` si le run est clos et `etat.status === "error"` ;
   - `"bloque"` si un événement `pipeline_done` de `etat.events` porte
     `final_status: "blocked"` — pour une file, un seul ticket bloqué suffit ;
   - `"termine"` si au moins un `pipeline_done` existe et que tous portent
     `final_status` `done` ou `in-review` ;
   - `"autre"` sinon (un chat, un run clos sans `pipeline_done`).
2. **`fermerRuns(runIds: string[])`** dans `useSupervision`, qui retire
   plusieurs cartes en une seule mise à jour d'état. `fermerRun` reste.
3. **Un menu « Fermer… »** dans la bande d'en-tête de `SupervisionView`
   (`frontend/src/components/SupervisionView/index.tsx`), à côté du compteur,
   avec quatre entrées : « Les terminés », « Les bloqués », « En erreur »,
   « Tous les runs clos ». Chaque entrée affiche son compte, par exemple
   « Les bloqués (2) », et est désactivée quand ce compte vaut zéro. Le menu
   n'apparaît pas quand aucun run n'est clos.
4. Si le run sélectionné fait partie des runs fermés, la sélection retombe
   sur la règle par défaut déjà en place (run en attente, sinon le premier) ;
   si le run revu en lecture seule (`revisuRun`) est fermé, la revue se ferme.

Couleurs : les libellés restent en `zinc` (ADR-026) ; aucune couleur d'état
n'est nécessaire, le compte suffit.

## Critères d'acceptation

- [ ] `issueDuRun.ts` existe, et `issueDuRun.test.ts` couvre chacun des cinq
      résultats, dont une file à deux tickets — l'un `done`, l'autre
      `blocked` — classée `"bloque"`
- [ ] Un test de `issueDuRun.test.ts` montre qu'un run non clos avec
      `status: "error"` rend `"en-cours"`
- [ ] `useSupervision.ts` exporte `fermerRuns` dans `UseSupervisionResult`, et
      un test de `useSupervision.test.ts` vérifie qu'il retire les runs
      nommés et garde les autres
- [ ] Un test de `SupervisionView.test.tsx` montre que « Les bloqués » retire
      les cartes des runs bloqués et laisse celles des runs terminés et du run
      en cours
- [ ] Un test de `SupervisionView.test.tsx` montre que « Tous les runs clos »
      ne retire jamais un run dont `runClosed` est faux
- [ ] Un test de `SupervisionView.test.tsx` montre qu'une entrée dont le compte
      vaut zéro est désactivée, et que le menu est absent sans run clos
- [ ] Un test de `SupervisionView.test.tsx` montre que fermer le lot qui
      contient le run sélectionné laisse le panneau sur un run restant
- [ ] Aucun fichier sous `backend/` n'est modifié

## Ce que ça ne fait pas

- Ne retire rien de l'historique (`RunHistorique`, onglet Stats) : la carte
  disparaît de Supervision, le run reste en base.
- Ne mémorise pas la fermeture d'une session à l'autre — inutile : au
  rechargement, l'instantané du backend ne contient déjà plus les runs clos.
- Pas de fermeture automatique au bout d'un délai : c'est l'utilisateur qui
  décide quand il a vu le résumé (ticket-267).

## Dépendances

Aucune.

## Estimation

Une demi-journée : un fichier pur, une fonction de hook, un menu.

## Risques

- Un `pipeline_done` sans `final_status` est lu `"done"` par `streamState`
  (`?? "done"`) : `issueDuRun` doit appliquer la même lecture, sinon un tel
  run tomberait en `"autre"`.