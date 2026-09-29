---
id: ticket-229
title: "Le backend démarre quand .env déclare FORBIDDEN_TERMS"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-09-29
---

# ticket-229 — Le backend accepte FORBIDDEN_TERMS

## Objectif

Poser la liste des termes interdits dans `.env`, comme le prévoit ADR-048, ne doit pas empêcher le backend de démarrer.

## Contexte

`Settings` refuse toute variable inconnue (`extra_forbidden`). Or ADR-048 fait vivre `FORBIDDEN_TERMS` dans `.env`, et aucun champ ne la déclarait : dès que la liste a été posée, `import tessera.config` a échoué, et toute la suite de tests avec lui (114 erreurs). Le backend en cours de route tournait encore, parce qu'il avait démarré avant, mais il ne serait jamais reparti.

## Solution

`Settings.forbidden_terms: str = ""`, documentée dans `.env.example` (vide). Le contrôle au push lui-même reste l'objet du ticket-206.

## Critères d'acceptation

- [x] Un test : un `.env` avec `FORBIDDEN_TERMS=alpha,beta` donne `forbidden_terms == "alpha,beta"`
- [x] Un test : sans la variable, `forbidden_terms` est vide
- [x] `.env.example` mentionne `FORBIDDEN_TERMS` (test existant `test_env_example_mentionne_chaque_variable_de_config`)
