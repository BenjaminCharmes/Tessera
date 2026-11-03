---
id: ticket-751
title: "The interpreter net covers node -e and Python named write modes"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-750"]
estimated_days: 1
created: 2026-11-03
---

# ticket-751 — Le filet d'interpréteur couvre `node -e` et le mode d'écriture nommé

## Objectif

Une écriture vers un fichier protégé passée à `node -e` ou à `python -c` avec un mode nommé
est refusée comme les formes déjà couvertes.

## Contexte

C-07 de `docs/audit/securite.md` (S-10), jamais ticketée. Le filet du ticket-326
(`backend/src/tessera/services/redirections_bash.py`) cherche `-c` : `node` lit son code
derrière `-e`, et `writeFileSync`/`appendFileSync` ne sont pas des motifs d'écriture. Côté
Python, `open(f, mode='w')` et `shutil.copy(...)` ne sont pas vus.

## Critères d'acceptation

- [ ] `test_node_e_write_to_a_protected_file_is_refused` : `node -e "require('fs').writeFileSync('agents.json','x')"`
      est refusé
- [ ] `test_python_open_with_named_mode_is_refused` : `python -c "open('agents.json', mode='w')"`
      est refusé
- [ ] Un test vérifie que `python -c "shutil.copy('a','agents.json')"` est refusé
- [ ] Un test vérifie que `node -e "console.log(1)"` passe

## Dépendances

ticket-750 (même fichier).
