---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-860
estimated_days: 1
id: ticket-861
pr_number: 958
priority: medium
status: done
title: The A-toi column and a recap panel show what the supervisor did
type: feat
---

# ticket-861 — La colonne « À toi » et un récap montrent ce que le superviseur a fait

## Objectif

Benjamin voit, au retour, « depuis ta dernière visite » : les actions du superviseur et les cas
qui l'attendent, sans ouvrir de fichier.

## Contexte

ADR-080, spec §2. `frontend/src/lib/bureau/aToi.ts` et `ColonneAToi.tsx` listent déjà ce qui
attend Benjamin (ticket-831 pour les leçons). Maquette d'abord pour toute interface : une
maquette Artifact Design avant d'écrire le composant, validation présumée.

## Ce qu'il faut faire

- `contenuAToi` ajoute par projet une ligne « N cas du superviseur à relire » quand
  `superviseur_a_toi` > 0 (aucune ligne à 0).
- Un panneau « Récap du superviseur » (lignes du journal, jour, action, cible, SHA court) ouvert
  depuis la colonne ; la date de dernière visite vit en `localStorage`. Couleurs d'état
  d'ADR-026 seulement, aucun texte en violet.
- Aucun bouton d'action : la lecture seule suit la route.

## Critères d'acceptation

- [ ] `aToi.test.ts` : une ligne « 2 cas du superviseur à relire » pour un projet qui en a deux,
      aucune pour zéro
- [ ] `ColonneAToi.test.tsx` : la ligne s'affiche avec le nom du projet
- [ ] `RecapSuperviseur.test.tsx` : le panneau liste les lignes depuis la date mémorisée
- [ ] `RecapSuperviseur.test.tsx` : un récap vide dit qu'il n'y a rien, sans erreur

## Ce que ça ne fait pas

Ne permet ni d'accepter ni de défaire depuis l'interface.