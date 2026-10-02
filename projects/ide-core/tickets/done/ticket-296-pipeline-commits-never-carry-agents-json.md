---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 0.5
id: ticket-296
pr_number: 185
priority: high
status: done
title: A pipeline commit never carries agents.json or another run-policy file
type: fix
---

# ticket-296 — Un commit du pipeline n'embarque jamais la politique du run

## Objectif

Qu'un réglage fait dans l'IDE pendant un run ne parte pas dans le commit du
ticket en cours.

## Contexte

Le 2026-10-01, le commit du ticket-279 (`a6b1545`) contenait une modification
de `projects/ide-core/agents.json` : `provider` et `fallback` ajoutés au rôle
`codeur`. Aucun agent ne peut écrire ce fichier (ADR-027). La modification
vient de l'écran Agents de l'IDE, utilisé pendant le run, et le commit du
pipeline, qui stage tout le dépôt (`:/` sous `git_root: ancestor`,
`services/git_workspace.py:515`), l'a ramassée avec le travail du codeur.

Le réglage a voyagé dans la PR d'un ticket qui n'en parlait pas, et l'aurait
mergé sans relecture. ADR-027 lit la politique une fois, avant le premier
agent : le pipeline n'a donc aucune raison de la commiter.

## Solution proposée

- Le commit d'un run exclut `agents.json`, `.claude/settings*.json` et
  `.github/workflows/`, comme il exclut déjà ses propres artefacts
  (`_exclude_pathspecs`).
- Une modification de ces fichiers présente au moment du commit reste dans
  l'arbre, non commitée, et le run le signale dans son rapport, sans
  échouer.

## Critères d'acceptation

- [ ] Un test sur un dépôt git temporaire vérifie qu'une modification
      d'`agents.json` faite pendant le run n'est pas dans le commit du ticket
- [ ] Un test vérifie que cette modification est toujours dans l'arbre après
      le commit
- [ ] Un test vérifie qu'un fichier de `.github/workflows/` modifié n'est pas
      commité non plus
- [ ] Un test vérifie que le travail du codeur, lui, est commité normalement

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Un arbre qui garde un `agents.json` modifié fait-il refuser le ticket suivant
par `ensure_clean_tree` ? Le tour de plan doit le vérifier : le ticket-278
tolère déjà les artefacts du pipeline, et la même tolérance doit couvrir ces
fichiers.