---
id: ticket-442
title: "Kanban, History, Supervision and Running use the shared status pill and buttons, and monospace is kept for copyable identifiers"
type: refactor
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-439"]
estimated_days: 1
created: 2026-10-14
---

# ticket-442 — Les écrans passent aux composants communs

## Objectif

Qu'un même état se dessine pareil sur tous les écrans, et que la police
monospace ne serve qu'à ce qui se copie.

## Contexte

Le ticket-439 pose `StatusPill` et `Button` dans `frontend/src/design/ui/`.
Audit du 2026-10-14 : chaque écran a sa pastille (Kanban : badges
`todo`/`high` ; Historique : coches et textes colorés ; Supervision :
« en cours », « tour 1 » ; En cours : « Tessera » / « Lancé à la main »)
et ses boutons. Les noms de rôles sont en monospace dans la liste des
agents, ce que la charte réserve aux ids, branches, chemins et commandes
(`projects/ide-core/memory/design.md`).

## Solution proposée

- Remplacer les pastilles d'état de `KanbanView` (statut), `HistoriqueView`,
  `SupervisionView` (statut du run) et `EnCoursView` (origine) par
  `StatusPill` avec la correspondance de la charte.
- Remplacer les boutons de ces quatre vues par `Button`, avec un seul
  `plein` par vue (l'action principale) et `arret` pour arrêter.
- Retirer le monospace des noms de rôles (`components/Sidebar/AgentList.tsx`)
  et des noms de services ; le garder pour ids de ticket, branches, chemins.

## Critères d'acceptation

- [ ] `KanbanView`, `HistoriqueView`, `SupervisionView` et `EnCoursView`
      importent `StatusPill` depuis `design/ui`
- [ ] Un test de `EnCoursView` vérifie que « Arrêter » est un `Button` en
      variante `arret`
- [ ] Un test de `AgentList` vérifie que le nom d'un rôle ne porte pas la
      classe `font-mono`
- [ ] Un test vérifie que chaque vue migrée a au plus un bouton en variante
      `plein`
- [ ] Les tests existants des quatre vues restent verts

## Dépendances

ticket-439.
