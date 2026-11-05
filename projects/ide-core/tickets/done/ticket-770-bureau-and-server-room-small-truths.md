---
id: ticket-770
title: "Working agents are counted from agent processes only, and two small Bureau slips"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-766"]
estimated_days: 1
created: 2026-11-03
---

# ticket-770 — Les agents au travail se comptent sur leurs seuls processus, et deux petits écarts du Bureau

## Objectif

Clore trois écarts relevés par l'audit du 30/10 (relecture du 03/11).

## Contexte

- `agents_en_cours` (`backend/src/tessera/services/salle_tessera.py`) compte tout descendant
  du backend dont la ligne de commande contient « claude » : les shells lancés pour l'outil
  Bash sourcent `~/.claude/shell-snapshots/…` et les serveurs MCP aussi, d'où un surcompte.
- La ronde du directeur (`frontend/src/lib/bureau/ronde.ts`, ticket-723) peut aller
  « féliciter le validateur » devant un poste vide sur un projet qui n'en a pas.
- `aria-controls` vaut `journal-${projet}-${nom}` : un nom de service avec une espace donne
  deux références.

## Critères d'acceptation

- [x] Un test vérifie que `agents_en_cours` ne compte qu'un processus dont l'exécutable est
      celui de l'agent (`claude.exe` ou le CLI), pas un shell dont la ligne contient « claude »
- [x] Un test vérifie que la ronde ne vise pas le poste du validateur quand le projet n'a pas
      de validateur actif
- [x] Un test vérifie que l'identifiant d'un journal dont le service s'appelle « mon api » ne
      contient pas d'espace

## Dépendances

ticket-766 (même fichier backend).
