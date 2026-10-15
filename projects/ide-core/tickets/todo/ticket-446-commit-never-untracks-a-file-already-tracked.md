---
id: ticket-446
title: "A run's commit never untracks a file the repository already tracked"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-15
---

# ticket-446 — Un commit de run ne désindexe jamais un fichier déjà suivi

## Objectif

Un projet en artefacts `local` dont le dépôt suit déjà `CLAUDE.md` (ou tout
autre artefact) ne doit pas voir ce fichier retiré de l'index par le commit
d'un run.

## Contexte

Vu deux fois : `portfolio` (04/10, `CLAUDE.md` retiré en silence) et
`make-your-call` (15/10, importé par `POST /projects/clone`, contourné en
passant le projet en `tracked`).

Le mode `local` écrit les artefacts dans `.git/info/exclude` (ADR-021). Avant
de commiter, `GitWorkspace._purger_stage_ignoré`
(`backend/src/tessera/services/git_workspace.py`) liste
`git ls-files --cached --ignored --exclude-standard` et fait
`git rm --cached` sur le résultat. Or cette liste inclut aussi les fichiers
**suivis dans `HEAD`** qu'une règle d'exclusion couvre après coup : un
`CLAUDE.md` versionné par le dépôt cloné en fait partie. Le commit du run
emporte alors sa suppression de l'index — exactement le `git rm --cached` que
le ticket-062 interdit de faire en silence.

La purge n'a été écrite que pour les fichiers **nouvellement** stagés qu'une
règle couvre (`test_run_interrompu_arbre_propre.py`).

## Solution proposée

Restreindre la purge aux chemins absents de `HEAD` : un fichier ignoré déjà
présent dans le commit de base reste dans l'index. Sur un dépôt sans commit
(`HEAD` absent), le comportement actuel est conservé.

## Critères d'acceptation

- [ ] `_purger_stage_ignoré` dans `git_workspace.py` ne passe à
      `git rm --cached` aucun chemin présent dans `HEAD`
- [ ] Un test crée un dépôt qui suit `CLAUDE.md`, ajoute `CLAUDE.md` à
      `.git/info/exclude`, appelle la purge, et vérifie que
      `git ls-files CLAUDE.md` le liste toujours
- [ ] Un test vérifie qu'un fichier nouvellement stagé et couvert par
      `.gitignore` est toujours retiré de l'index
- [ ] Les tests existants de `test_run_interrompu_arbre_propre.py` sont
      inchangés

## Ce que ça ne fait pas

- Ne change pas le mode par défaut d'un projet cloné (`local`, ADR-023).
- Ne restaure pas un fichier déjà désindexé par un run passé.

## Risques

Un fichier suivi que l'utilisateur veut réellement sortir du dépôt reste
suivi : c'est voulu, ce retrait se décide (ticket-062).
