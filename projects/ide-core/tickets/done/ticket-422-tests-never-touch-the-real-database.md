---
agent: codeur
created: 2026-10-13
depends_on: []
estimated_days: 0.5
id: ticket-422
pr_number: 417
priority: medium
status: done
title: The backend test suite never writes into the real tessera.db
type: fix
---

# ticket-422 — Les tests n'écrivent jamais dans la vraie base

## Objectif

Qu'un lancement de la suite backend — par le testeur du pipeline, sur la
machine où tourne Tessera — ne laisse aucune trace dans `backend/tessera.db`.

## Contexte

Le 2026-10-13, `pipeline_runs` de la base de production contenait un run
ouvert pour un projet `projet-pr` / `ticket-001`, inexistant : c'est le
projet que crée `tests/test_refus_livraison_impossible.py` (ticket-413). Ses
tests démarrent un vrai run (202) via `TestClient(app)` ; `settings.ide_db_path`
n'est pas redirigé, donc le run est enregistré dans la vraie base. Un run
ouvert y fausse la procédure de redémarrage (liste des runs ouverts) et les
statistiques.

## Solution proposée

- Dans `backend/tests/conftest.py`, une fixture `autouse` de portée session
  (ou fonction) qui pointe `settings.ide_db_path` vers un fichier dans
  `tmp_path_factory` et initialise son schéma, pour **tous** les tests.
- Un test garde-fou : il vérifie que `settings.ide_db_path` n'est pas le
  chemin par défaut du dépôt pendant la suite.
- Les tests qui fixaient déjà leur propre base continuent de le faire.

## Critères d'acceptation

- [ ] `backend/tests/conftest.py` redirige `settings.ide_db_path` vers un
      fichier temporaire pour tous les tests
- [ ] Un test vérifie que, pendant la suite, `settings.ide_db_path` est sous
      le dossier temporaire de pytest et non `backend/tessera.db`
- [ ] Un test vérifie qu'un run démarré par `POST /orchestrator/run` dans un
      test est enregistré dans la base temporaire

## Dépendances

Aucune.