---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 0.5
id: ticket-425
pr_number: 422
priority: medium
status: done
title: Switching project keeps the current tab and view instead of jumping to the
  tickets
type: fix
---

# ticket-425 — Changer de projet ne fait plus quitter l'onglet en cours

## Objectif

Qu'on puisse passer d'un projet à l'autre — par une carte de la vue Projets,
par le sélecteur en tête de colonne ou par la liste de la colonne — sans être
renvoyé à chaque fois sur la liste des tickets.

## Contexte

Retour de Benjamin le 2026-10-14 : « lorsqu'on clique sur un projet depuis
la vue Projets, ça renvoie directement sur la vue Tickets. Même chose avec
toutes les façons de changer de projet ». Pour lancer ou regarder plusieurs
projets d'affilée, il faut revenir à la vue Projets après chaque clic.

`handleSelectProject` (`frontend/src/hooks/useCockpit.ts`) fait deux choses
au changement de projet :

1. `setPanel(panelAfterProjectSwitch(panel))` — et
   `panelAfterProjectSwitch` renvoie `"tickets"` depuis `"projects"` ;
2. `setShowKanban(true)` — le centre repasse sur la liste des tickets, quel
   que soit l'onglet.

## Solution proposée

- `panelAfterProjectSwitch` renvoie toujours le panneau courant (le garder
  comme fonction nommée, documentée, pour le jour où une exception serait
  voulue).
- `handleSelectProject` ne touche plus à `showKanban` : la vue du centre
  reste celle que l'utilisateur avait choisie.
- Dans la vue Projets, un clic sur une carte sélectionne le projet (barre
  violette, colonne de gauche à jour) et reste sur la vue Projets.
- Ce qui doit continuer de se réinitialiser au changement de projet le
  reste : fichier ouvert (`openFilePath`), flux du run affiché
  (`stream.clear()`).

## Critères d'acceptation

- [ ] `useCockpit.test.ts` vérifie que `panelAfterProjectSwitch("projects")`
      renvoie `"projects"`, et que les autres panneaux sont conservés
- [ ] Un test vérifie que changer de projet ne modifie pas `showKanban`
      (vue liste reste liste, vue tableau reste tableau)
- [ ] Un test de `ProjetsView` (ou d'`App`) vérifie qu'un clic sur une carte
      rend ce projet actif et laisse la vue Projets affichée
- [ ] Un test vérifie que changer de projet ferme le fichier ouvert

## Dépendances

Aucune.

## Ce que ça ne fait pas

- Ne donne pas encore à Fichiers, Historique et Agents leur propre vue
  centrale : sujet à part, maquette d'abord.