---
agent: architect
created: 2026-11-04
depends_on:
- ticket-754
estimated_days: 1
id: ticket-780
pr_number: null
priority: low
status: done
title: Design global settings that can be changed from the interface, without a restart
type: design
---

# ticket-780 — Concevoir des réglages globaux modifiables depuis l'interface, sans redémarrage

## Objectif

Les réglages globaux qu'on change en pratique se modifient depuis Tessera, sans éditer `.env`
ni redémarrer le backend.

## Contexte

03/11 : passer `MAX_PARALLEL_TEST_RUNS` de 3 à 2 a demandé d'éditer `.env`, de redémarrer le
backend et de prévenir chaque session ouverte. Le bouton « Réglages » du rail ne montrait que
des valeurs en lecture : il a été retiré (ticket-779), il reviendra avec de vrais réglages.
Les réglages vivent dans `backend/src/tessera/config.py` (Pydantic, lus au démarrage).

Candidats : `run_max_budget_usd`, `llm_max_budget_usd`, `max_parallel_test_runs`,
`keep_awake_during_runs`, `dialogue_timeout_s`.

## Ce que la conception doit fixer

- La liste retenue, et ce qui n'y figure jamais : les secrets (jetons, `STATIC_TOKEN`,
  `FORBIDDEN_TERMS`, ADR-053) et les réglages par projet (`agents.json`).
- Le stockage : en SQLite, par-dessus les valeurs par défaut de `.env`, sans jamais réécrire
  `.env` ; et la valeur effective lue partout au même endroit.
- Le moment où un changement s'applique : au run suivant, jamais au milieu d'un run.
- La sécurité : l'API est ouverte quand `STATIC_TOKEN` est vide ; relever un plafond de
  dépense ne doit pas être à la portée d'une page locale quelconque (dépend de ticket-754).
- L'interface : un bouton au pied du rail, avec une icône d'engrenage sans ambiguïté.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md` répond à
      chacun des points ci-dessus, avec sa règle sous `## Proposées` de `contraintes.md`
- [ ] Les tickets d'implémentation sont créés dans `projects/ide-core/tickets/todo/`, chacun
      tient en moins d'une journée et nomme ses tests
- [ ] Aucun code n'est écrit par ce ticket

## Dépendances

ticket-754 (origines admises par l'API).