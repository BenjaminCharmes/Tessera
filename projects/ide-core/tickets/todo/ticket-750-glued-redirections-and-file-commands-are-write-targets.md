---
id: ticket-750
title: "Glued redirections, every tee argument and cp mv rm targets are write targets"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-750 — Redirections collées, tous les arguments de `tee`, et `cp`/`mv`/`rm` sont des cibles d'écriture

## Objectif

Le contrôle d'écriture Bash lit les formes simples de redirection et les commandes de
fichiers les plus courantes.

## Contexte

C-06 de `docs/audit/securite.md` (S-11), jamais ticketée ; reconfirmée le 03/11.
`backend/src/tessera/services/redirections_bash.py` ne rend pas comme cible : un jeton collé
(`echo x>../f`), `2>../f`, `1>`, `&>`, `>|` (rend la cible `'|../f'`), le second fichier de
`tee a ../b`, un chemin Windows à antislash (mangé par `shlex` en mode POSIX). `cp`, `mv`,
`rm` ne sont pas lus : `rm -r ../autre-projet` n'est pas une écriture pour le garde. ADR-031
borne la promesse à « une erreur, pas une évasion » : ce sont des erreurs ordinaires.

## Critères d'acceptation

- [ ] `test_glued_redirection_is_a_target` : `echo x>../f`, `echo x 2>../f`, `echo x 1>../f`,
      `echo x &>../f` et `echo x >|../f` rendent la cible `../f`
- [ ] `test_every_tee_argument_is_a_target` : `tee a ../b` rend `a` et `../b`
- [ ] `test_cp_mv_rm_targets_outside_the_root_are_refused` : `cp x ../y`, `mv x ../y`,
      `rm -r ../autre` sont refusés hors de la racine, et passent dedans
- [ ] `test_windows_backslash_path_is_not_eaten` : `echo x > ..\f` rend `..\f`
