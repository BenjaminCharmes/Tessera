---
id: ticket-756
title: "Link roots are bounded wherever the file API reads them"
type: fix
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-747"]
estimated_days: 1
created: 2026-11-03
---

# ticket-756 — Les racines de lien sont bornées partout où l'API fichiers les lit

## Objectif

Un lien symbolique du workspace qui vise un dossier trop large n'ouvre pas ce dossier en
écriture par l'API fichiers.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-707. `_workspace_roots`
(`backend/src/tessera/routers/fs.py`) ajoute la cible de tout lien enfant du workspace sans
repasser par `_refuse_too_broad` (`backend/src/tessera/services/project_importer.py`), qui
ne s'applique qu'à l'import. Un lien créé avant le ticket, ou autrement que par l'import,
garde sa cible en écriture.

## Critères d'acceptation

- [ ] Un test vérifie qu'un lien `workspace/x → Path.home()` ne rend pas
      `Path.home()/f.txt` écrivable par `PUT /fs/write` (403)
- [ ] Un test vérifie qu'un lien vers un dossier de projet ordinaire reste écrivable

## Dépendances

ticket-747 (même routeur).
