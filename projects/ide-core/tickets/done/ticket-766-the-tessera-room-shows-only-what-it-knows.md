---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-766
pr_number: null
priority: medium
status: done
title: The Tessera server room shows only what it knows
type: fix
---

# ticket-766 — La salle Tessera ne montre que ce qu'elle sait

## Objectif

Les compteurs et voyants de la salle serveur Tessera disent vrai (ADR-058, ADR-026).

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-726.
- `runs_du_jour` (`backend/src/tessera/services/salle_tessera.py`) compte aussi les
  enveloppes de file et d'autonome : une file de 5 tickets affiche 6 runs, les statistiques 5
  (`usage_stats.py` filtre `mode IS NULL OR mode = 'single'`).
- La baie GPU (`frontend/src/components/EnCoursView/SalleTessera.tsx`) affiche
  « Disponible » quand `refroidissement_s === null`, qui veut seulement dire « jamais coupé » :
  Ollama arrêté s'affiche disponible.
- Le voyant « derniers runs » (`EcransDeTessera.tsx`) est vert dès que `approved !== false`,
  donc aussi sans verdict ; vert veut dire approuvé.

## Critères d'acceptation

- [ ] Un test vérifie qu'une base avec une enveloppe de file et deux runs enfants donne
      `runs_du_jour == 2`
- [ ] Un test vérifie que l'infobulle de la baie GPU sans refroidissement ne contient pas
      « Disponible »
- [ ] Un test vérifie que le voyant des derniers runs est vert seulement pour `approved === true`
      et zinc pour un run sans verdict