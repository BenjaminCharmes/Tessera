---
agent: codeur
created: 2026-11-03
depends_on:
- ticket-746
estimated_days: 1
id: ticket-749
pr_number: null
priority: medium
status: done
title: Common Windows and Git Bash wrappers are unwrapped by the git guard
type: fix
---

# ticket-749 — Le garde git déballe les enveloppes courantes de Windows et Git Bash

## Objectif

Une commande git en écriture lancée par une enveloppe naturelle sous Windows ou Git Bash est
vue par le garde.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-703. Passent (vérifié) : `cmd //c "git push"`
(forme obligatoire sous Git Bash : `_OPTIONS_CMD` ne connaît que `/c`, `/k`),
`powershell git push` (sans `-Command`), `-EncodedCommand`, `echo push origin | xargs git`
(`git_interdit([])` rend faux), `env -u HOME git push`, `timeout -s KILL 30 git push`
(l'option à valeur arrête `sans_enveloppe`), `setsid`/`stdbuf`/`flock` inconnus. Le ticket
703 ne vise pas l'évasion délibérée (`g=git; $g push`) : ce ticket non plus.

## Solution proposée

Ajouter `//c` et `//k` ; relire `powershell`/`pwsh` sans option comme une ligne de commande
et refuser `-EncodedCommand` ; refuser `xargs git` quand git n'a pas de sous-commande ; faire
consommer leur valeur aux options connues des enveloppes (`-u`, `-s`, `-k`, `-a`, `-n`) ;
ajouter `setsid`, `stdbuf`, `flock` aux enveloppes.

## Critères d'acceptation

- [ ] Un test vérifie que `cmd //c "git push"`, `powershell git push` et
      `powershell -EncodedCommand ZwBpAHQA` sont refusés
- [ ] Un test vérifie que `echo push | xargs git`, `env -u HOME git push`,
      `timeout -s KILL 30 git push` et `stdbuf -oL git push` sont refusés
- [ ] Un test vérifie que `xargs git status` et `timeout 30 git log` passent

## Dépendances

ticket-746 (même garde).