---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-864
estimated_days: 1
id: ticket-865
pr_number: null
priority: low
status: done
title: A review button launches a project review and shows its cost
type: feat
---

# ticket-865 — Un bouton « Revue » lance une revue de projet et en montre le coût

## Objectif

Benjamin lance une revue depuis la fiche d'un projet, voit le coût plafonné avant, puis suit le
run comme n'importe quel autre.

## Contexte

ADR-080, spec §4. Maquette Artifact Design avant l'interface, validation présumée. Un run se
suit sur `WS /orchestrator/observe` (ADR-041) ; rien de nouveau à observer.

## Ce qu'il faut faire

- Un bouton « Revue du projet » sur la fiche d'un projet, qui interroge le coût estimé de la
  route (ticket-864), l'affiche avec le plafond de 3 $ et demande confirmation.
- Projet occupé (409) : message qui nomme le ticket en cours ; aucun second clic possible.
- Après lancement : le run apparaît dans le fil comme les autres, sans écran propre.
- Couleurs d'état d'ADR-026, hooks seulement, pas de `any`.

## Critères d'acceptation

- [ ] `RevueProjetBouton.test.tsx` : le coût estimé et le plafond s'affichent avant confirmation
- [ ] `RevueProjetBouton.test.tsx` : un 409 affiche le ticket en cours et désactive le bouton
- [ ] `RevueProjetBouton.test.tsx` : annuler la confirmation n'envoie aucune requête de lancement

## Ce que ça ne fait pas

Ne montre pas les tickets produits : ils arrivent dans le Kanban comme tout ticket.