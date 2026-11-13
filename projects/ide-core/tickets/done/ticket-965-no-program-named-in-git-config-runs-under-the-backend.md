---
agent: codeur
created: 2026-11-13
depends_on: []
estimated_days: 0.5
id: ticket-965
pr_number: 1111
priority: high
status: done
title: No program named in a project's git config runs when the backend commits or
  diffs
type: fix
---

# ticket-965 — Aucun programme nommé dans la config git d'un projet ne s'exécute quand le backend commite ou lit un diff

## Objectif

Qu'une clé écrite dans `.git/config` par un agent ne fasse rien exécuter au
backend, sous son compte, y compris au commit de blocage qui suit sa
détection.

## Contexte

Audit du lot 941-961 (13/11). `services/noyau/git_commande.py`,
`build_command`, ne force que `core.fsmonitor=false` (ticket-933, 941) et,
pour une écriture, `core.hooksPath`. Si un agent contourne la garde et écrit
dans `.git/config` `commit.gpgsign=true` avec `gpg.program=<script>`, ou un
`filter.<nom>.clean` avec un `.gitattributes`, l'empreinte (ADR-084) le voit et
met le run en `blocked`. Mais le commit de blocage (`bloquer`, appelé par
`pipeline_empreinte.arret_fichier_protege`, ADR-037) lance alors `git add` et
`git commit`, qui exécutent le script sous le compte du backend.

## Solution proposée

1. `build_command` force aussi, pour toute commande : `commit.gpgsign=false`,
   `tag.gpgSign=false`, `gpg.program=`, `core.sshCommand=`, `diff.external=`,
   `core.pager=cat`.
2. Les lectures de diff du backend passent `--no-ext-diff` et
   `--no-textconv`.
3. Quand l'empreinte a vu changer la config git du dépôt, le commit de
   blocage ne se fait pas avec cette config : il restaure d'abord la config
   d'avant le run (l'empreinte la porte), ou, à défaut, ne commite pas et
   laisse l'arbre tel quel en le journalisant (`commit_de_blocage_saute`).
   Un `filter.*` ne se neutralise pas par `-c` sans connaître son nom.

## Critères d'acceptation

- [ ] Un test : `build_command` contient `commit.gpgsign=false`,
      `gpg.program=`, `core.sshCommand=` et `diff.external=` pour une
      lecture comme pour une écriture.
- [ ] Un test sur un vrai dépôt `tmp_path` : avec `commit.gpgsign=true` et un
      `gpg.program` qui écrit un fichier témoin, un commit fait par le backend
      réussit et le fichier témoin n'existe pas.
- [ ] Un test sur un vrai dépôt : avec un `filter.x.clean` qui écrit un
      fichier témoin et un `.gitattributes` qui l'applique, ajoutés pendant le
      run, le run finit en `blocked` et le fichier témoin n'existe pas.
- [ ] Un test : les commandes de diff du backend portent `--no-ext-diff` et
      `--no-textconv`.

## Ce que ça ne fait pas

- Ne change pas la détection par empreinte (ADR-084) ni la liste des
  fichiers protégés.
- En mode compte dédié, l'ACL en lecture seule sur `.git` reste la première
  défense (ticket-947).