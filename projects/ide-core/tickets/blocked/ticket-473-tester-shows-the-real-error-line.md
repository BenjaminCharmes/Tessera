---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.5
id: ticket-473
pr_number: null
priority: medium
status: blocked
title: A failed test step reports its first error line, not only the package manager's
  ELIFECYCLE
type: fix
---

# ticket-473 — Le testeur remonte la vraie ligne d'erreur

## Objectif

Quand une étape du `test_command` échoue, le résumé du testeur montre la
ligne qui dit pourquoi, pas seulement la dernière ligne du gestionnaire de
paquets.

## Contexte

Souhaito, 16/10, ticket-002 bloqué après trois tours. Au tour 3, `tsc` et
`vitest` passaient ; seul `check:build` échouait parce que le codeur avait
réécrit `scripts/check-build.mjs` pour lancer `pnpm run build`, et `pnpm`
nu n'est pas sur le PATH du testeur (qui passe par `corepack`). La sortie
contenait « 'pnpm' n'est pas reconnu en tant que commande interne… », mais
le résumé transmis au codeur et au journal ne montrait que
`ELIFECYCLE Command failed with exit code 1`. Le codeur n'avait aucun moyen
de comprendre ; la session du projet a dû lire la sortie brute.

`backend/src/tessera/services/test_runner.py` garde, faute de section de
résumé reconnue (pytest, vitest), les dernières lignes de la sortie
(`_LIGNES_DE_QUEUE`).

## Solution proposée

- Quand l'extraction structurée ne trouve rien, chercher dans la sortie de
  l'étape la **première** ligne qui ressemble à une erreur (`error`,
  `Error:`, `n'est pas reconnu`, `not recognized`, `command not found`,
  `ENOENT`, `Cannot find module`) et la placer en tête du détail, avant la
  queue actuelle.
- Si cette ligne signale une commande introuvable (`pnpm`, `npm`, `yarn`,
  `npx`), ajouter une phrase : « commande introuvable dans l'environnement du
  testeur : passer par corepack ou par node_modules/.bin ».

## Critères d'acceptation

- [ ] Un test vérifie qu'une sortie contenant « 'pnpm' n'est pas reconnu »
      puis « ELIFECYCLE » donne un détail qui commence par la ligne « n'est
      pas reconnu »
- [ ] Le même test vérifie que la phrase sur corepack et
      node_modules/.bin est présente
- [ ] Un test vérifie que `command not found` (sortie Unix) est traité de
      même
- [ ] Un test vérifie qu'une sortie pytest garde son extraction structurée
      actuelle