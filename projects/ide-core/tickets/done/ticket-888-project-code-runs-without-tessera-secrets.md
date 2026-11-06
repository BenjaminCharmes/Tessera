---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 0.5
id: ticket-888
pr_number: null
priority: high
status: done
title: Every process that runs project code gets an environment without Tessera's
  secrets
type: fix
---

# ticket-888 — Le code d'un projet tourne sans les secrets de Tessera

## Objectif

Les tests, les services, l'app du contrôle visuel et les captures d'un projet
démarrent avec un environnement d'où les secrets de Tessera et les jetons
GitHub sont vidés, comme celui des agents.

## Contexte

Audit externe du 06/11 (Fable, sans contexte), vérifié. Le ticket-873 a vidé
les secrets de l'environnement des agents (`env_du_sous_processus`,
`backend/src/tessera/services/providers/env_sdk.py`). Mais le code des projets,
qu'un agent écrit, est lancé par le backend avec tout son environnement :
`backend/src/tessera/services/verification/test_runner.py` passe
`{**os.environ, **self._env}`, ou `None`, qui hérite de tout. Avec
`SECRETS_SOURCE=env` ou un secret exporté dans le shell qui a lancé le backend,
un test écrit par l'agent lit `GITHUB_TOKEN` ou `ANTHROPIC_API_KEY`.

C'est une classe entière de lancements, pas un seul : même héritage dans
`backend/src/tessera/services/verification/process_registry.py` (services),
`app_du_run.py` (contrôle visuel), `captures.py` et `groupe_d_etape.py`, dans
le même dossier. Les commandes `git` du backend ne sont pas concernées : le
push de la livraison a besoin du jeton.

## Solution proposée

Une fonction publique `env_du_code_de_projet(extra: Mapping[str, str] | None)
-> dict[str, str]`, dans `services/verification/` ou plus bas : une copie de
`os.environ` où chaque nom de `NOMS_SECRETS` (`backend/src/tessera/coffre.py`),
`GITHUB_TOKEN` et `GH_TOKEN` est retiré, puis `extra` par-dessus. Chacun des
cinq modules l'utilise au lieu de `os.environ` ou de `env=None`.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_env_du_code_de_projet.py` vérifie qu'avec
      `GITHUB_TOKEN`, `GH_TOKEN` et un nom de `NOMS_SECRETS` posés dans
      l'environnement (monkeypatch), l'environnement rendu ne les contient pas.
- [ ] Un test vérifie qu'une variable ordinaire (`PATH`) et une clé d'`extra`
      sont conservées.
- [ ] Un test vérifie, avec un double de `asyncio.create_subprocess_exec`, que
      `test_runner.py` lui passe un `env` sans `GITHUB_TOKEN`, y compris quand
      le runner n'a pas d'`_env` propre.
- [ ] Le diff remplace l'héritage de `os.environ` (ou `env=None`) par
      `env_du_code_de_projet` dans `test_runner.py`, `process_registry.py`,
      `app_du_run.py`, `captures.py` et `groupe_d_etape.py`.
- [ ] Un test de `backend/tests/test_env_du_code_de_projet.py` lit le texte de
      ces cinq modules et échoue si l'un d'eux contient `**os.environ` ou
      `env=None`.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Une suite de tests qui lisait volontairement un de ces secrets échoue : aucune
ne doit le faire, c'est le but.