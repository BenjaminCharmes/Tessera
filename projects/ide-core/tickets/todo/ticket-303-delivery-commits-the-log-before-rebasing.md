---
id: ticket-303
title: "Delivery commits the pipeline's pending log lines before it rebases"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-02
---

# ticket-303 — La livraison commite le journal avant de rebaser

## Objectif

Qu'une livraison ne s'arrête plus sur « cannot rebase: You have unstaged
changes » quand la seule modification est le journal du pipeline.

## Contexte

Le 2026-10-02, la livraison du ticket-289, approuvé, s'est arrêtée net :

```
git rebase develop
error: cannot rebase: You have unstaged changes.
```

Seul `projects/ide-core/memory/pipeline-log.md` était modifié. Depuis le
ticket-288, le pipeline journalise des durées après son commit de tenue de
livres (documentation, puis étapes de livraison). Le ticket-301 a appris à
`is_clean` à tolérer ce journal, mais `git rebase` exige un arbre
entièrement propre, sans exception. Sans PR, le ticket suivant de la file
s'est empilé sur le 289 non livré.

Les livraisons précédentes passaient : un commit de documentation emportait
souvent ces lignes avec lui. Le 289 n'a modifié aucun fichier de
documentation, et rien n'a été commité après sa ligne de journal.

## Solution proposée

Juste avant `rejouer_sur`, la livraison commite ce qui reste des artefacts de
tenue de livres (`commit_bookkeeping`, déjà utilisé en fin de run). Elle
n'appelle rien d'autre : un fichier de code modifié doit toujours faire
échouer la livraison, comme aujourd'hui.

## Critères d'acceptation

- [ ] Un test sur un dépôt git temporaire vérifie qu'une livraison dont seul
      le journal est modifié rebase sans erreur
- [ ] Un test vérifie que les lignes de journal en attente sont dans un
      commit `chore: tessera pipeline bookkeeping` de la branche, avant le
      rebase
- [ ] Un test vérifie qu'un fichier de code modifié fait toujours échouer la
      livraison, avec un `arret` qui le dit

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Les lignes journalisées pendant la livraison, après le rebase, restent non
commitées : le ticket-301 les tolère, et le run suivant les commitera.
