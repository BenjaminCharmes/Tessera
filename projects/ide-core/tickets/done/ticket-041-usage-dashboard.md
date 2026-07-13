---
id: ticket-041
title: "Dashboard coût et usage des appels Claude"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-07-13
---

# ticket-041 — Dashboard coût et usage des appels Claude

## Objectif

Offrir une vue dédiée dans la sidebar pour suivre la consommation API (tokens et coût $)
par projet, avec un breakdown par ticket. L'endpoint `GET /api/v1/projects/{id}/usage`
est déjà disponible (ticket-040) — ce ticket est 100 % UI.

## Contexte

Depuis ticket-040, chaque appel LLM est persisté avec son coût. La seule surface UI
actuelle est un chiffre en amber dans les détails dépliés d'un run dans RunHistory.
On veut un panneau dédié accessible depuis la sidebar.

## Solution proposée

### Nouveau composant `UsageDashboard`

Panneau affiché dans la sidebar (sous Historique ou via un onglet dédié) qui contient :

- **Résumé global** : coût total, tokens totaux, nombre de runs
- **Tableau par ticket** : ticket_id | appels | tokens | coût — trié par coût décroissant
- **Formatage** : coûts en `$0.0000`, tokens en `1 234 567` avec séparateurs

### Intégration

- Nouveau hook `useUsage(projectId)` qui appelle `GET /api/v1/projects/{id}/usage`
- Rafraîchissement à chaque fois que le panneau devient visible (ou bouton refresh)
- Zéro état si aucun run n'a encore été lancé

## Critères d'acceptation

- [ ] Un panneau "Usage" est accessible depuis la sidebar pour le projet sélectionné
- [ ] Il affiche coût total, tokens totaux, nombre de runs
- [ ] Il affiche un tableau des tickets avec leur coût, trié par coût décroissant
- [ ] Si aucun run, un empty state explicite est affiché
- [ ] Les données se rafraîchissent quand le panneau s'affiche

## Dépendances

ticket-040 (done) — endpoint `/usage` existant.

## Estimation

**1j** — Essentiellement UI : hook + composant + intégration sidebar.
