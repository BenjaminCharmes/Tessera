---
id: ticket-1060
title: "The coder bench reuses one existing Python environment instead of creating one per copy"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-1057]
estimated_days: 1
created: 2026-11-27
---

# ticket-1060 — Le banc du codeur réutilise un seul environnement Python existant

## Objectif

Les cellules du banc font tourner leurs tests dans un environnement Python unique, déjà créé, au lieu d'en créer un par copie.

## Contexte

`banc_codeur_roles.py` lance `uv sync --frozen --extra dev` dans `backend/` de chaque copie sans historique, et
`uv run` y crée un `.venv` neuf, donc un `python.exe` neuf. Depuis le 27/11 vers 11 h, Smart App Control refuse ces
lanceurs neufs (os error 4551) et affiche une alerte Windows à chaque essai. Les environnements déjà créés
marchent. Les cellules d'un essai tournent en série : un environnement partagé peut être resynchronisé sur le
`uv.lock` de chaque copie avant ses tests. Un environnement créé par `uv venv`, ou par un `uv sync` sans
`UV_PROJECT_ENVIRONMENT`, crée un exe : c'est interdit ici.

## Solution proposée

Dans `scripts/banc_codeur_roles.py`, une fonction `environnement_partage()` lit la variable d'environnement
`BANC_VENV` et renvoie le dossier d'un venv qui existe déjà. Elle refuse, en levant `EnvironnementRefuse`
(une `RuntimeError`) : une variable absente ou un chemin relatif ; un dossier sans interpréteur
(`Scripts/python.exe` ou `bin/python`) ; le `.venv` du checkout `backend/` de Tessera (son backend tourne dessus).
Elle ne crée jamais le dossier. Une fonction `env_des_commandes(venv)` renvoie une copie de `os.environ` où
`UV_PROJECT_ENVIRONMENT` vaut ce dossier. `_lancer` passe ce dictionnaire en `env=` à `subprocess.run` pour
`COMMANDE_ENV` et `COMMANDE_TESTS` ; `os.environ` du processus n'est pas modifié, donc l'agent codeur ne le
reçoit pas. `COMMANDE_ENV` et `COMMANDE_TESTS` ne changent pas. `roles_reels` appelle `environnement_partage()`
à la construction : sans environnement valide, le banc s'arrête avant le premier appel payant.

## Critères d'acceptation

- [ ] `environnement_partage()` de `scripts/banc_codeur_roles.py` renvoie le dossier désigné par `BANC_VENV` quand
      il contient `Scripts/python.exe` ou `bin/python`, et un test le couvre.
- [ ] Un test couvre chaque refus de `environnement_partage()` : variable absente, chemin relatif, dossier sans
      interpréteur, dossier égal au `.venv` de `backend/` du dépôt courant.
- [ ] Un test couvre `environnement_partage()` sur un dossier inexistant : il lève `EnvironnementRefuse` et ne
      crée rien.
- [ ] `env_des_commandes(venv)` renvoie un dictionnaire dont `UV_PROJECT_ENVIRONMENT` vaut `str(venv)`, sans
      modifier `os.environ`, et un test le couvre.
- [ ] Un test remplace `subprocess.run` et vérifie que `_lancer` le reçoit avec `env=` portant
      `UV_PROJECT_ENVIRONMENT`, pour la commande d'environnement et pour celle des tests.
- [ ] Aucun appel de `scripts/banc_codeur*.py` ne contient `"venv"` comme argument de commande ni `uv venv`
      (un test lit les sources).
- [ ] `COMMANDE_ENV` garde `--frozen` et `--extra dev`, `COMMANDE_TESTS` finit par `--impact base`
      (`test_env_and_tests_install_and_keep_the_dev_extra` reste vert).
- [ ] Ni `backend/src/`, ni `agents.json`, ni `agents/prompts/` ne sont modifiés.

## Ce que ça ne fait pas

- Ne crée aucun environnement et ne choisit pas lequel servir : l'humain pose `BANC_VENV`.
- Ne contourne pas Smart App Control : aucune copie d'exe, aucune politique touchée.
- Ne rend pas les cellules parallèles : l'environnement partagé suppose une cellule à la fois.
- Ne change ni `verifier.py`, ni le reviewer, ni le validateur.

## Dépendances

ticket-1057.

## Estimation

Une journée au plus : une fonction, un paramètre `env=`, des tests.

## Risques

Un `uv sync` peut réinstaller des paquets à DLL jugés par Smart App Control ; ce risque existait déjà par copie.
