---
agent: codeur
created: 2026-11-03
depends_on:
- ticket-740
estimated_days: 1
id: ticket-755
pr_number: 882
priority: medium
status: done
title: A red retest followed by no test command still stops the delivery
type: fix
---

# ticket-755 — Un retest rouge suivi d'« aucune commande de test » arrête quand même la livraison

## Objectif

Un premier retest rouge n'est jamais effacé par un second essai qui ne trouve plus de
commande de test.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-718. `juger`
(`backend/src/tessera/services/retest_apres_rebase.py`) relance une fois un premier essai
rouge ; si le second rend `None` (`TestCommandNotFound`, par exemple parce que le premier a
supprimé `pyproject.toml`), `juger` rend `None` et la livraison part sans trace. Vérifié avec
un lanceur factice (rouge, puis `None`) : `jugement: None`.

## Critères d'acceptation

- [ ] `test_red_then_no_command_still_stops` : un premier essai rouge puis un second `None`
      rendent un `Jugement` dont `arret` est posé, avec la sortie du premier essai
- [ ] Un test vérifie qu'un premier essai `None` rend toujours `None` (projet sans test)

## Dépendances

ticket-740 (même zone de livraison).