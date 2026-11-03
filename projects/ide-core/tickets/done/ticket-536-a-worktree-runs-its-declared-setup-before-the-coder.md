---
agent: codeur
created: 2026-10-22
depends_on: []
estimated_days: 1
id: ticket-536
pr_number: 601
priority: medium
status: done
title: A worktree runs its declared setup command before the coder starts
type: feat
---

# ticket-536 — Un worktree lance sa préparation déclarée avant le codeur

## Objectif
Que le codeur d'un run en worktree dispose des dépendances du projet (types
des bibliothèques) dès son premier tour.

## Contexte
Signalé par Kadoomi le 22/10 (ticket-087). Un worktree neuf n'a pas de
`node_modules` : `populate` n'en lie pas exprès (une jonction a vidé un
`node_modules` le 14/10), et seul le testeur l'installe, par la première étape
de sa `test_command`. Le codeur ne peut donc pas lire les types : au premier
tour du 087, il a inventé un hook (`onEmailVerification`) qui n'existe pas, et
il a fallu un tour de plus.

## Solution proposée
Une clé facultative `worktree.setup` (chaîne) dans `agents.json`, validée par
`services/worktree_politique.py` avec le reste de `ConfigWorktree`. Après la
création et le peuplement du worktree, avant le codeur, la commande tourne
dans le worktree avec `worktree.env`, sous le délai du testeur
(`pipeline.test_timeout_s`). Un échec ou un dépassement de délai met le run en
`blocked` avec la sortie de la commande, sans appeler le codeur (ADR-037).
Absente : rien ne change.

## Critères d'acceptation
- [ ] `ConfigWorktree` dans `models/worktree_config.py` porte un champ `setup: str | None = None`, et `lire_worktree` le valide (une valeur qui n'est pas une chaîne invalide la déclaration, comme `test_command`)
- [ ] Un test vérifie, avec des doubles, que la commande `setup` tourne dans le worktree, avec `worktree.env`, avant le premier appel au codeur
- [ ] Un test vérifie qu'une commande `setup` en échec met le run en `blocked` sans appeler le codeur
- [ ] Un test vérifie qu'un projet sans `setup` n'exécute aucune commande avant le codeur

## Ce que ça ne fait pas
- Ne déclare `setup` dans l'`agents.json` d'aucun projet : c'est à la main
  (ADR-027). Pour Kadoomi, ce sera `corepack pnpm@10 install --frozen-lockfile`.