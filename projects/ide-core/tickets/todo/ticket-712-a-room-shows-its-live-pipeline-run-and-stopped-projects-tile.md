---
id: ticket-712
title: "A room shows its project's live pipeline run, and stopped projects become compact tiles"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-710"]
estimated_days: 1
created: 2026-10-30
---

# ticket-712 — Une salle montre le run du pipeline en cours sur son projet, et les projets arrêtés deviennent des tuiles

## Objectif
On voit depuis la salle d'un projet qu'une file Tessera y travaille, et sur
quel ticket. Les projets arrêtés n'occupent plus une ligne pleine largeur
chacun.

## Contexte
Pendant que Curio tourne, sa file de tickets avance (ticket-059, étape de
relecture), mais sa salle n'en dit rien. `useSupervision`
(`frontend/src/hooks/useSupervision.ts`) donne les runs ouverts avec leur
`project_id`. Pour chacun, le store de run (`frontend/src/hooks/runStore.ts`,
`StreamState` dans `streamState.ts`) porte `ticketId`, `queue`
(`{index, total}`) et `currentAgent`.
Les douze projets arrêtés (`ProjetsArretes.tsx`) prennent chacun une ligne
pleine largeur, avec un bouton à l'autre bout de l'écran.

Maquette : `projects/ide-core/design/maquette/Salle-des-serveurs-v2.dc.html`.

## Solution proposée
- Quand `useSupervision` porte un run ouvert pour le `project_id` de la salle :
  - un poste de travail dans la salle, avec `ticketId` et le rôle de `currentAgent` ;
  - un badge bleu sur la plaque (« File 3/6 · ticket-059 » pour une file,
    l'id du ticket seul sinon).
  Sans run, rien de tout cela (ADR-058).
- Sur la plaque, un lien « Ouvrir » par port de service, vers
  `http://localhost:<port>`.
- Les projets arrêtés deviennent une grille de tuiles compactes (nom et bouton
  « Lancer »), de plusieurs colonnes selon la largeur disponible.

## Critères d'acceptation
- [ ] Un test : avec un run ouvert sur le projet (`useSupervision` et store de run simulés), la salle affiche son `ticketId` et son `currentAgent` ; sans run, ni poste ni badge
- [ ] Un test : un run dont `queue` vaut `{index: 3, total: 6}` affiche « 3/6 » dans le badge
- [ ] Un test : la plaque porte un lien `href="http://localhost:8026"` pour un service au port 8026
- [ ] Un test de `ProjetsArretes` : chaque projet arrêté est une tuile avec son bouton « Lancer », et le conteneur est une grille
- [ ] `EnCoursView.test.tsx` rend l'écran « En cours » avec un run vivant et y trouve le poste de run dans la bonne salle

## Ce que ça ne fait pas
- Pas de pilotage de la file depuis la salle (arrêt, relance)
- Pas de date de dernier lancement sur les tuiles : aucune donnée ne la porte aujourd'hui
