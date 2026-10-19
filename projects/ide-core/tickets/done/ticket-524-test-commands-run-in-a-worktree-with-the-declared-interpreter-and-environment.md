---
agent: codeur
created: 2026-10-19
depends_on:
- ticket-521
estimated_days: 0.5
id: ticket-524
pr_number: null
priority: medium
status: done
title: Test commands run in a worktree with the declared interpreter and environment
type: feat
---

# ticket-524 — Les tests tournent dans le worktree, avec l'interpréteur déclaré

## Objectif
Qu'un `test_command` puisse s'exécuter dans un worktree sans `uv`, avec
l'interpréteur du `.venv` principal et `PYTHONPATH` pointé sur le worktree.

## Contexte
Spec § 3. `uv` est refusé par le contrôle d'applications dans un worktree : les
tests y tournent avec `PYTHONPATH=<wt>/backend/src` et le `python.exe` du
`.venv` principal (essais du 14/10). `TestRunnerService._lancer`
(`services/test_runner.py`) lance sans environnement propre ;
`controles_depart.py` vérifie le premier mot de `test_command`.

## Ce qu'il faut faire
- Fonction pure `commande_effective(politique, racine_worktree, depot) -> str |
  None` : `worktree.test_command` s'il est déclaré, sinon `test_command`, avec
  `{worktree}` et `{repo}` remplacés. Un placeholder inconnu n'est pas remplacé
  et la commande est refusée avec une raison claire. Fonction pure
  `environnement_effectif(config, racine_worktree, depot) -> dict[str, str]`,
  mêmes placeholders.
- `TestRunnerService.__init__` gagne `env: Mapping[str, str] | None = None`,
  fusionné **par-dessus** `os.environ` pour chaque étape. Sans `env`, le
  comportement est identique à aujourd'hui.
- `controles_depart` vérifie le premier mot de la commande **effective**, résolu
  depuis le `test_cwd` du dossier du projet dans le worktree.
- Le script que la commande lance reste refusé en écriture (ADR-027), résolu dans
  le worktree : un test le confirme.

## Tests
- [ ] `backend/tests/test_commande_effective.py` : override présent / absent ; `{worktree}` et `{repo}` remplacés ; placeholder inconnu refusé ; `env` fusionné avec les placeholders
- [ ] `backend/tests/test_test_runner.py` (ou le fichier existant du runner) : une commande qui affiche une variable d'`env` la voit ; sans `env`, l'environnement hérité est inchangé
- [ ] `controles_depart` : un premier mot introuvable dans la commande effective est signalé ; le même mot introuvable dans la commande **non utilisée** ne l'est pas
- [ ] `test_chemins_proteges.py` : le script de la commande effective se refuse en écriture dans le worktree

## Critères d'acceptation
- [ ] Les quatre blocs de tests ci-dessus existent et passent
- [ ] Les tests existants du runner et de `controles_depart` passent sans modification de leurs assertions
- [ ] Rien n'appelle encore ces fonctions avec un worktree : le branchement est le ticket-519

## Dépendances
Ticket 521.

## Ce que ça ne fait pas
Ne crée aucun worktree. Ne règle pas le blocage de l'entrée standard (ticket-512).