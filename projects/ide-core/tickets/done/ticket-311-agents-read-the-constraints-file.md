---
agent: codeur
created: 2026-10-02
depends_on:
- ticket-310
estimated_days: 1
id: ticket-311
plan: true
pr_number: null
priority: high
status: done
title: Agents read the short constraints file instead of the whole decision log
type: feat
---

# ticket-311 — Les agents lisent les contraintes, plus le journal

## Objectif

Faire lire aux agents `memory/contraintes.md` (ticket-310), réduit par rôle,
à la place de `memory/decisions.md`, sans perdre aucune règle en route.

## Contexte

Le ticket-310 a classé les 51 ADR et rédigé les règles en vigueur, avec leurs
numéros d'ADR. Aujourd'hui, `services/adr.py` découpe `decisions.md` et
`agent_runner.py:252` l'injecte dans le prompt (`adr_pertinents`). Le
`CLAUDE.md` à la racine du dépôt l'importe aussi (`@projects/ide-core/memory/decisions.md`),
pour les sessions de développement.

Le danger est la régression silencieuse : une règle qui disparaît du prompt
ne fait échouer aucun test, et un agent se met simplement à l'ignorer. Les
garde-fous ci-dessous la rendent visible.

## Solution proposée

- Le prompt des agents reçoit `memory/contraintes.md`, réduit au rôle appelé,
  sur la même règle que la portée d'ADR-032 : une règle sans portée part à
  tous. Si `contraintes.md` est absent, on retombe sur `decisions.md`, pour
  les projets importés qui n'en ont pas.
- Un test de traçabilité : chaque ADR de `decisions.md` sans `**Portée**`,
  classé « règle » ou « fusion » dans `memory/adr-audit.md`, est cité dans
  `contraintes.md`.
- Le budget de `contraintes.md` est mesuré, comme celui des ADR
  (`test_consignes_coherentes.py`).
- **Ce ticket autorise la modification du `CLAUDE.md` à la racine du dépôt**
  (règle 5), limitée à remplacer l'import de `decisions.md` par celui de
  `contraintes.md` dans la section « Contexte toujours chargé », et au
  paragraphe qui l'explique.

## Critères d'acceptation

- [ ] Un test vérifie que le prompt d'un codeur contient une règle de
      `contraintes.md` et ne contient plus le titre d'un ADR classé
      « histoire » (par exemple ADR-004, Tauri plutôt qu'Electron)
- [ ] Un test vérifie qu'une règle portée par d'autres rôles n'arrive pas au
      validateur
- [ ] Un test vérifie que, sans `contraintes.md`, le prompt reçoit
      `decisions.md` comme avant
- [ ] Le test de traçabilité décrit ci-dessus existe et passe
- [ ] Un test vérifie que `contraintes.md` reste sous 12 000 caractères
- [ ] Le `CLAUDE.md` racine importe `contraintes.md` et plus `decisions.md`

## Dépendances

ticket-310.

## Risques

Toute nouvelle décision devra désormais s'écrire à deux endroits : l'ADR
dans le journal, et sa règle dans `contraintes.md`. Le test de traçabilité
est ce qui empêche d'oublier le second.