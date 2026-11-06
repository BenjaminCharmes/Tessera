---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-850
- ticket-851
estimated_days: 1
id: ticket-858
pr_number: null
priority: medium
status: done
title: The supervisor reopens a queue cut by the infrastructure
type: feat
---

# ticket-858 — Le superviseur rouvre une file coupée par l'infrastructure

## Objectif

Une file interrompue par une coupure (veille, réseau, redémarrage) reprend avec ses tickets
restants ; une file interrompue par un verdict reste interrompue.

## Contexte

ADR-080, spec §2 (`relancer_file`). Le journal du 04 et 05/11 montre « file interrompue »
pour ticket-759, ticket-750 et ticket-793, tous « non approuvé » : une décision de qualité, à
ne pas relancer. Les coupures par veille ou réseau (nuit du 04/11, `GitCommandError` du
ticket-753) se distinguent par leur cause.

## Ce qu'il faut faire

- `services/supervision/superviseur_file.py`, sans modèle : classer la cause d'une interruption
  (`infrastructure` | `verdict` | `introuvable` | `inconnue`) depuis la ligne du journal du
  pipeline ; seule `infrastructure` se relance, et seulement si `relance_file` est vrai
  (ticket-852).
- Une relance par cause et par file ; la file restante est rouverte par le chemin du planificateur
  (ADR-041), plafond de dépense et quota réel vérifiés comme en mode autonome (ADR-020). Quota
  inconnu : ne bloque pas.
- Deux interruptions de même cause de suite : « À toi », pas de troisième relance (ADR-078).

## Critères d'acceptation

- [ ] `test_superviseur_file.py::test_network_cut_is_classified_infrastructure`
- [ ] `test_superviseur_file.py::test_unapproved_ticket_is_classified_verdict_and_not_relaunched`
- [ ] `test_superviseur_file.py::test_missing_ticket_is_never_relaunched`
- [ ] `test_superviseur_file.py::test_one_relaunch_per_cause_per_queue`
- [ ] `test_superviseur_file.py::test_relaunch_is_off_unless_declared`
- [ ] `test_superviseur_file.py::test_spent_daily_budget_blocks_the_relaunch`

## Ce que ça ne fait pas

Ne relance jamais un ticket non approuvé. Ne démarre jamais une file que personne n'avait ouverte.