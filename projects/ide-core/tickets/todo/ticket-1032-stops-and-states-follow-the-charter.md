---
agent: codeur
created: 2026-11-20
depends_on: []
estimated_days: 1
id: ticket-1032
priority: low
status: todo
title: Stops, states and project cards follow the charter
type: fix
---

# ticket-1032 — Arrêts, états et cartes de projet suivent la charte

## Objectif

Quatre écarts entre l'interface et la charte, relevés en construisant la page
Composants de la maquette (`projects/ide-core/design/maquette/Composants.dc.html`,
lignes « Écart »), se referment. Décidés par délégation le 13/11.

## Contexte

La charte (`design/maquette/Charte.dc.html`) dit : « un arrêt est bordé de
rouge, jamais plein » et « un état : fond teinté à 12 %, texte clair de la
même famille ». `frontend/src/design/ui/StatusPill.tsx` porte déjà cette
forme (`bg-blue-500/12 text-blue-300`, etc.). Quatre endroits ne la suivent
pas :

1. `frontend/src/components/Sidebar/RemoveProjectModal.tsx` : le bouton
   « Confirmer la suppression » est plein (`bg-red-800 … hover:bg-red-700`).
2. `frontend/src/components/Sidebar/ticketCardTables.ts` : `STATUS_STYLE`, lu
   par le sélecteur de statut de `TicketCard.tsx`, donne des fonds pleins
   (`bg-blue-900`, `bg-red-900`…), alors que la même carte rend déjà
   `StatusPill` quand le statut n'est pas modifiable.
3. `frontend/src/components/Toast.tsx` : `TYPE_STYLE` donne des fonds pleins
   (`bg-green-800`, `bg-red-800`, `bg-zinc-700`).
4. `frontend/src/components/ProjetsView/ProjetCarte.tsx` : la carte est en
   `rounded-sm` (2 px) ; la maquette la dessine à 10 px de rayon.

## Solution proposée

1. Bouton « Confirmer la suppression » : contour rouge, sans fond plein —
   `border border-red-500/60 text-red-300 hover:bg-red-950/40`, le reste
   inchangé.
2. `STATUS_STYLE` : les teintes de la pastille, par la correspondance
   `STATUS_ETAT` déjà dans le fichier — `todo` et `cancelled` en
   `bg-zinc-500/12 text-zinc-300`, `in-progress` en `bg-blue-500/12
   text-blue-300`, `in-review` en `bg-amber-500/12 text-amber-300`, `done` en
   `bg-green-500/12 text-green-300`, `blocked` en `bg-red-500/12 text-red-300`.
3. Toast : un toast flotte au-dessus du contenu, un fond à 12 % seul serait
   illisible. Le conteneur du toast devient opaque (`bg-zinc-900`, bordure
   `border border-zinc-700`) et la teinte se pose sur une couche intérieure :
   `bg-green-500/12 text-green-300` (succès), `bg-red-500/12 text-red-300`
   (erreur), `bg-zinc-500/12 text-zinc-300` (info). `role`, `aria-live`,
   `data-type`, icône et bouton de fermeture ne changent pas.
4. `ProjetCarte` : `rounded-[10px]` à la place de `rounded-sm` sur la carte.
   Ni la hauteur ni la taille du titre ne changent.

## Critères d'acceptation

- [ ] Un test de `frontend/src/components/Sidebar/RemoveProjectModal.test.tsx`
      vérifie que le bouton « Confirmer la suppression » porte une classe de
      bordure rouge et aucune classe `bg-red-800` ni `bg-red-700`.
- [ ] Un test vérifie que chaque valeur de `STATUS_STYLE`
      (`frontend/src/components/Sidebar/ticketCardTables.ts`) contient un fond
      en `/12` et aucun fond en `-900`, `-800` ou `-700`.
- [ ] Un test de `frontend/src/components/Toast.test.tsx` vérifie, pour un
      toast d'erreur, que l'élément `role="status"` ou un de ses descendants
      porte `bg-red-500/12`, que le conteneur opaque porte `bg-zinc-900`, et
      qu'aucun élément ne porte `bg-red-800`.
- [ ] Un test de `frontend/src/components/ProjetsView/ProjetCarte.test.tsx`
      vérifie que la carte porte `rounded-[10px]` et pas `rounded-sm`.
- [ ] `frontend/src/design/coherence.test.ts` passe sans être modifié.
- [ ] `tsc`, `eslint` et `vitest` passent.

## Ce que ça ne fait pas

- Ne touche ni `AgentBadge`, ni `StageStrip`, ni `QualityCard`, qui ont leurs
  propres couleurs.
- Ne change ni la hauteur ni le titre des cartes de projet.
- Ne modifie pas la maquette : ses lignes « Écart » se retirent à la main
  après la livraison.

## Dépendances

Aucune.

## Estimation

Une heure.

## Risques

Le sélecteur de statut est un `<select>` natif : sa liste déroulante reste
lisible parce que `index.css` déclare `color-scheme: dark`. À contrôler à
l'œil après la livraison.
