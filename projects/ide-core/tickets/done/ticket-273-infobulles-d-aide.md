---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 1
id: ticket-273
pr_number: 147
priority: medium
status: done
title: Explanations move into an info tooltip; states and calls to action stay visible
type: feat
---

# ticket-273 — Les explications passent en infobulle, les états restent visibles

## Objectif

Alléger l'interface : un texte qui **explique** s'affiche au survol d'une icône
d'information ; un texte qui dit un **état** ou **ce qu'il faut faire** reste
affiché.

## Contexte

Demande utilisateur du 2026-09-30, à partir du réglage des notifications :
« Notifications — quand un agent pose une question, qu'un run se bloque ou
finit » est affiché en permanence alors que c'est une explication lue une
fois.

La règle qui départage :
- **explication** (ce que fait un réglage, pourquoi une chose existe) → infobulle ;
- **état** (« bloquées par le navigateur : à autoriser dans ses réglages de
  site », « coupées »), **appel à l'action** (« Sélectionne un projet pour… »),
  **erreur** → reste visible. Les masquer ferait manquer l'information au
  moment où elle compte.

Aucun composant d'infobulle n'existe hors des graphiques (`design/charts/`).

## Solution proposée

- Créer `design/InfoTip.tsx` : une icône d'information (à ajouter à
  `design/icons.tsx`, grille de 24, trait 1.5) et un texte qui s'affiche au
  survol **et au focus clavier** ; l'icône est un `button` avec
  `aria-describedby` vers le texte, `role="tooltip"`. Couleurs : zinc, pas de
  violet en texte (ADR-026).
- L'appliquer à :
  1. `Sidebar/ReglageNotifications.tsx` — seul le libellé de l'état `actives`
     passe en infobulle ; `coupees`, `bloquees`, `indisponibles` restent
     affichés ;
  2. `AgentDetail/index.tsx` — « Ce texte est envoyé en tête de chaque appel… » ;
  3. `Sidebar/BranchCleanup.tsx` — « Elles ne contiennent rien qui ne soit déjà
     dans la base » ;
  4. `Sidebar/PanneauServices.tsx` — « La commande est lancée telle quelle,
     sans shell… » ;
  5. `Sidebar/ImportProjectModal.tsx` — « Les repos privés nécessitent un
     token… ».
- Les états vides et les messages d'erreur ne sont pas touchés.

## Critères d'acceptation

- [ ] `design/InfoTip.tsx` existe, et un test montre que son texte est rendu
      avec `role="tooltip"` au survol comme au focus de l'icône.
- [ ] Un test montre que l'icône d'`InfoTip` est un bouton relié à son texte
      par `aria-describedby`.
- [ ] Un test de `ReglageNotifications` montre qu'à l'état `actives`, le texte
      « quand un agent pose une question » n'est pas affiché hors survol.
- [ ] Un test de `ReglageNotifications` montre qu'à l'état `bloquees`, le texte
      « bloquées par le navigateur » reste affiché en permanence.
- [ ] Les quatre autres textes listés sont rendus via `InfoTip` dans le diff.
- [ ] Le diff n'ajoute aucune balise `<svg>` hors de `frontend/src/design/`.

## Dépendances

Aucune.

## Estimation

1 jour. Frontend uniquement.

## Risques

Une infobulle au seul survol est invisible au clavier et sur écran tactile :
le focus doit l'ouvrir, et `Échap` la fermer.