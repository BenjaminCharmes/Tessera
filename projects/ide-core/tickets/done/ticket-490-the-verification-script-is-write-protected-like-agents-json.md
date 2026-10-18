---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.5
id: ticket-490
pr_number: null
priority: medium
status: done
title: The verification script a run is judged by is write-protected, and a diff that
  touches test configuration is flagged to the reviewer
type: fix
---

# ticket-490 — Le script de vérification n'est pas modifiable par le run qu'il juge

## Objectif

Un codeur ne peut pas affaiblir, dans son propre diff, la vérification qui
juge ce diff.

## Contexte

Signalé le 16/10 par une session de lecture du code (aucun run en cause).
`test_command` vient d'`agents.json`, protégé en écriture (ADR-027). Mais sur
ide-core, il lance `../scripts/verifier.py`, que le testeur exécute **depuis la
branche du run**. Aucun garde-fou ne couvre ce fichier : le hook `PreToolUse`
refuse `agents.json`, `.git/`, `.claude/settings*.json` et
`.github/workflows/`, mais pas le script que `test_command` désigne. Un codeur
peut donc retirer une étape (mypy, eslint…) dans le même diff que celui
qu'elle doit juger. Seul le reviewer pourrait s'en apercevoir, et rien ne
l'y invite.

Le même problème se pose, en plus diffus, pour la configuration des tests
(`conftest.py`, `[tool.pytest]`, `vitest.config.*`, scripts de
`package.json`) : la modifier est souvent légitime, et ne peut donc pas être
interdit.

## Solution proposée

1. **Le script de `test_command` est protégé en écriture.** Au démarrage
   d'un run, le chemin du script est extrait de `test_command` : le premier
   argument qui désigne un fichier existant, résolu depuis `pipeline.test_cwd`.
   Le hook `PreToolUse` le refuse en écriture, comme `agents.json`, avec un
   message qui dit pourquoi. Si aucun fichier n'est désigné (`npm test`,
   `uv run pytest`), rien de plus n'est protégé.
2. **Un diff qui touche la configuration des tests est signalé.** Si le diff
   du run modifie un fichier de cette liste fermée — `conftest.py`,
   `pyproject.toml` (section `[tool.pytest*]` ou `[tool.mypy]`),
   `vitest.config.*`, `eslint.config.*`, `tsconfig*.json`, la clé `scripts`
   de `package.json` —, le message du reviewer commence par un avertissement
   qui nomme ces fichiers et lui demande de vérifier que la vérification n'est
   pas affaiblie. Une ligne le note dans `pipeline-log.md`.

Un ticket qui doit modifier le script de vérification lui-même se fait à la
main, hors pipeline : c'est rare (tickets 295 et 304).

## Ce que ça ne fait pas

- Ne lance pas le script depuis la branche de base. Cette piste a été
  écartée : un ticket qui ajoute un test au script verrait l'ancienne version,
  et la base n'est pas toujours extraite sur le disque.
- N'empêche pas un codeur d'affaiblir un test : c'est le rôle du reviewer et
  du validateur, que l'avertissement aide.

## Critères d'acceptation

- [ ] Un test vérifie que le hook refuse l'écriture de `scripts/verifier.py`
      quand `test_command` vaut `uv run python ../scripts/verifier.py` et que
      `test_cwd` est `backend/`
- [ ] Un test vérifie qu'avec `test_command` à `npm test`, aucun fichier
      supplémentaire n'est refusé
- [ ] Un test vérifie qu'un diff qui touche `conftest.py` ou `vitest.config.ts`
      fait commencer le message du reviewer par l'avertissement qui les nomme
- [ ] Un test vérifie qu'un diff sans aucun de ces fichiers ne porte pas
      d'avertissement
- [ ] La règle est ajoutée à `memory/contraintes.md`, sous ADR-027