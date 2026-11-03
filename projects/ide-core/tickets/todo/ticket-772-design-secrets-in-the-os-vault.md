---
id: ticket-772
title: "Design how Tessera keeps its secrets in the operating system vault instead of a plain .env"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-772 — Concevoir le rangement des secrets dans le coffre du système

## Objectif

Les jetons de Tessera (`ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, jetons des services en ligne,
`STATIC_TOKEN`) ne vivent plus en clair dans `.env`.

## Contexte

Un comparatif externe du 03/11 avec un IDE comparable classe la sécurité de Tessera à 58/100,
d'abord pour ses clés en clair dans `.env` ; l'autre IDE les range dans le Gestionnaire
d'identification Windows. ADR-053 interdit déjà à un agent de lire `.env` ; le fichier reste
lisible par tout processus de l'utilisateur. Côté Python, la bibliothèque `keyring` sait
lire et écrire le coffre de Windows, de macOS et de Linux.

## Ce que la conception doit fixer

- Quels secrets passent au coffre, et ce qui reste dans `.env` (réglages non secrets).
- La lecture au démarrage (`settings`), le repli quand le coffre est indisponible (CI,
  Docker, Linux sans trousseau), et l'échec fermé quand un secret manque.
- La migration depuis un `.env` existant (commande `tessera.ps1`), sans jamais réécrire un
  secret en clair.
- Ce que deviennent `FORBIDDEN_TERMS` et le hook `pre-push` (ADR-050), qui lisent `.env`.
- Les garde-fous d'ADR-053 qui protègent aujourd'hui `.env`, à étendre au coffre.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md` répond à
      chacun des points ci-dessus, avec sa règle sous `## Proposées` de `contraintes.md`
- [ ] Les tickets d'implémentation sont créés dans `projects/ide-core/tickets/todo/`, chacun
      tient en moins d'une journée et nomme ses tests
- [ ] Aucun code n'est écrit par ce ticket
