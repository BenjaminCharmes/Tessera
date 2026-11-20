---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-851
- ticket-852
- ticket-854
estimated_days: 1
id: ticket-856
pr_number: 956
priority: high
status: done
title: The supervisor decides a delegated lesson or rule
type: feat
---

# ticket-856 — Le superviseur décide une leçon ou une règle déléguée

## Objectif

Une leçon sous `## Proposées` de `memory/lecons.md`, ou une règle sous `## Proposées` de
`memory/contraintes.md`, est acceptée ou écartée par le superviseur quand le projet l'a
délégué ; sinon elle reste, et passe dans « À toi » si elle est sensible.

## Contexte

ADR-080 (amende ADR-055 et ADR-074), spec §2 (`decider`). Benjamin l'a délégué à la session
« ide-core » le 05/11, modèle fort pour les décisions sensibles ; restent à lui : argent,
suppression, secrets, professionnel.

## Ce qu'il faut faire

- `services/supervision/superviseur_decision.py` : pour chaque bloc proposé, dossier borné (le
  bloc, l'ADR cité, la section voisine, 8 Ko), modèle du rôle (Opus par défaut, ticket-852).
- Ordre des gardes : (1) la délégation `lecons` ou `regles` est déclarée, sinon rien ; (2)
  `est_sensible` sur le bloc et sur l'ADR qu'il cite : vrai → `a_toi`, sans appeler le modèle ;
  (3) modèle : `agir` accepte ou écarte, `a_toi` escalade, jamais plus laxiste que (2).
- Accepter déplace le bloc vers sa section ; `deplacement_pur` vérifie le diff avant le commit ;
  écarter retire le bloc et le journalise avec la raison. Les deux passent par `intervenir`.
- Plafond : 5 décisions par intervention, le reste au balayage suivant.

## Critères d'acceptation

- [ ] `test_superviseur_decision.py::test_without_delegation_nothing_moves`
- [ ] `test_superviseur_decision.py::test_sensitive_rule_goes_to_a_toi_without_calling_the_model`
- [ ] `test_superviseur_decision.py::test_model_cannot_accept_what_the_filter_flagged`
- [ ] `test_superviseur_decision.py::test_accepted_lesson_moves_to_en_vigueur_and_nothing_else_changes`
- [ ] `test_superviseur_decision.py::test_rule_naming_the_supervisor_is_never_accepted`
- [ ] `test_superviseur_decision.py::test_discard_removes_the_block_and_logs_the_reason`

## Ce que ça ne fait pas

Ne réécrit jamais le texte d'un bloc. Ne touche pas à `decisions.md`.