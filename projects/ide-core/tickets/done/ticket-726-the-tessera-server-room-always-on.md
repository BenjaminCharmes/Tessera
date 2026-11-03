---
id: ticket-726
title: "The Tessera server room, always on"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-30
---

# ticket-726 — La salle des serveurs de Tessera, toujours allumée

## Objectif
Tessera a sa propre salle en tête de « En cours », sur toute la largeur, qui montre
ce qui fait tourner l'IDE.

## Contexte
Idée de Benjamin le 30/10, maquette validée
(`projects/ide-core/design/maquette/Salle-des-serveurs-v2-tessera.dc.html`). Tessera tourne
toujours, mais n'avait pas de salle : ses agents sont au Bureau, et ses serveurs
ne sont pas des apps de projet.

## Fait
- `GET /api/v1/tessera/salle` (`routers/salle_tessera.py`, `services/salle_tessera.py`) :
  les processus du backend (lui seul, sans les agents des runs) et du Vite (5173,
  avec son arbre) lus par la sonde de l'inventaire, l'état de refroidissement
  d'Ollama (`secondes_de_refroidissement`), les runs vivants et leur file, les PR que
  le CIWatcher attend, la fin de `tessera.log` réduite au nom de l'événement (ni
  chemin ni charge), la taille de la base et le nombre de worktrees.
- `SalleTessera` : encadrée de violet (identité, ADR-026), sans bouton d'arrêt ; trois
  moniteurs (runs et file, CIWatcher, journal), une baie par serveur avec la fiche
  partagée, une baie GPU (`BaieGpu`) ambre et clignotante pendant le refroidissement,
  le quota de la semaine et sa remise à zéro, la base et les worktrees.
- `MoniteurMural` partagé par les écrans des services (ticket-711) et ceux de la salle.
Fait à la main avec Benjamin, servi sur 5175.

## Critères d'acceptation
- [x] `backend/tests/test_salle_tessera.py` : processus, file, journal sans charge, worktrees, base, refroidissement, PR en attente et la route
- [x] `SalleTessera.test.tsx` : en tête même sans app, sans bouton d'arrêt ; écrans, baies, GPU en refroidissement, quota, base et worktrees ; écrans vides qui le disent ; absente de la vue Liste
