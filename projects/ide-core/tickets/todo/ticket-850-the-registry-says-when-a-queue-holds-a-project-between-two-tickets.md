---
id: ticket-850
title: "The registry says when a queue holds a project between two tickets"
type: feat
status: todo
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-05
pr_number: null
---

# ticket-850 — Le registre dit qu'une file tient un projet, y compris entre deux tickets

## Objectif

`RunRegistry.projet_tenu_par_file(project_id)` est vrai de l'ouverture à la fermeture d'une file,
y compris pendant le court instant où aucun ticket n'est actif.

## Contexte

ADR-080, spec §5. Le verrou est relâché entre deux tickets (ADR-051). Un écrivain étranger qui
s'y glisse fait échouer le ticket suivant en 409 et interrompt la file. `RunActif.file`
(`FileVivante`) existe déjà (`run_registry.py`) ; il faut lire à quel moment l'entrée disparaît
entre deux tickets.

## Ce qu'il faut faire

- Ajouter `RunRegistry.projet_tenu_par_file(project_id: str) -> bool`, sans nouvelle structure
  parallèle : s'appuyer sur ce que le registre sait déjà (ADR-034). Si l'entrée est détruite
  entre deux tickets, la file se déclare ouverte au registre pour toute sa durée, et se retire
  à sa fermeture, y compris sur exception (ADR-037).
- Le mode autonome et le planificateur comptent comme des files.

## Critères d'acceptation

- [ ] `test_run_registry.py::test_queue_holds_project_between_two_tickets`
- [ ] `test_run_registry.py::test_queue_releases_project_when_it_closes`
- [ ] `test_run_registry.py::test_queue_releases_project_on_exception`
- [ ] `test_run_registry.py::test_single_run_is_not_a_queue`
- [ ] `test_run_registry.py::test_autonomous_mode_counts_as_a_queue`

## Ce que ça ne fait pas

Ne refuse aucun run : `RunLock` garde son comportement (ADR-038). Seul le futur superviseur lit ce
prédicat.
