---
id: ticket-219
title: "Un run interrompu laisse l'arbre propre, journal compris"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-28
---

# ticket-219 — Un run interrompu laisse l'arbre propre

## Objectif

Après un run interrompu, `git status` est vide : le prochain run démarre sans intervention.

## Contexte

Sur un run interrompu (limite de tours, provider tombé), le pipeline commite le travail puis ses fichiers de suivi. Il écrit **ensuite** la ligne « INTERROMPU au tour N » dans `memory/pipeline-log.md`, et ne la commite jamais. C'est arrivé deux fois le 2026-09-28 (tickets 203 et 213). À chaque fois, l'arbre est resté sale, et le run suivant aurait été refusé par `ensure_clean_tree` (ADR-018).

## Solution proposée

La ligne de journal de fin de run s'écrit avant le commit de suivi, ou elle est incluse dans ce commit, quel que soit le chemin de sortie : approuvé, refusé, bloqué par la sécurité ou interrompu.

## Critères d'acceptation

- [x] Un test : run interrompu par une exception du codeur → aucun fichier modifié ni non suivi après la fin du run
- [x] Un test : la ligne « INTERROMPU » figure dans le dernier commit de la branche
- [x] Les chemins approuvé et refusé gardent leur comportement (tests existants verts)
- [x] `uv run pytest` passe

## Dépendances

Aucune.

## Estimation

0,5 jour.
