---
id: ticket-250
title: "Chaque information n'a plus qu'une place à l'écran"
type: refactor
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-29
---

# ticket-250 — Chaque information n'a plus qu'une place à l'écran

## Objectif

Supprimer les doublons d'affichage relevés par l'audit UI : la colonne
latérale vide à côté d'une seconde colonne, les deux sélecteurs de projet,
les coûts affichés deux fois, et le libellé « Vue liste » qui trompe.

## Contexte

Pour les panneaux Chat et Supervision, la colonne 2 (280 px) reste vide
pendant que le chat crée sa propre liste de conversations dans le centre
(`ChatPanel/ConversationSidebar.tsx`, `w-44`). Le menu `SelecteurDeProjet`
(ProjectHeader) et la liste `ProjectNav` (panneau Projets) permettent tous
deux de changer de projet. `UsageDashboard` (colonne 2) et `StatsView`
(centre) montrent les coûts en même temps. Le bouton « Vue liste »
(`TicketList.tsx:172`) n'affiche pas une liste : il ouvre l'éditeur du ticket.

## Solution proposée

Panneau Chat : la liste des conversations devient le contenu de la colonne 2
(rendue par `Sidebar`), le centre ne garde que la conversation. Sélecteur de
projet : **écarté à l'implémentation** — la coexistence du menu de
`ProjectHeader` (bascule rapide sans perdre la vue courante) et du panneau
Projets (gestion : import, création, retrait) est un choix documenté par le
ticket-174, pas une dérive ; retirer l'un des deux serait une régression.
Coûts : le panneau Usage bascule le centre sur `StatsView` et la colonne 2
n'affiche plus `UsageDashboard` en parallèle (au plus un résumé d'une ligne).
Renommer « Vue liste » en « Éditeur ».

## Critères d'acceptation

- [ ] Avec le panneau Chat actif, la colonne 2 liste les conversations et le centre n'a plus de colonne `ConversationSidebar`
- [ ] Le double accès au changement de projet (en-tête + panneau Projets) est conservé et documenté comme choix du ticket-174 dans la solution proposée
- [ ] Les coûts ne s'affichent plus simultanément dans la colonne 2 et au centre
- [ ] Le bouton de bascule du centre dans l'en-tête des tickets dit « Éditeur », plus « Vue liste »
- [ ] Les tests existants de `ChatPanel`, `Sidebar` et `TicketList` sont mis à jour et un test couvre le rendu des conversations dans la colonne 2

## Dépendances

Aucune.

## Estimation

2 jours.

## Risques

Le déplacement des conversations remonte de l'état de `ChatPanel` vers
`App`/`Sidebar` : attention au nombre de props (ticket-252 découpe ensuite).
