---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-750
pr_number: null
priority: medium
status: done
title: Glued redirections, every tee argument and cp mv rm targets are write targets
type: fix
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

- [x] `test_glued_redirection_is_a_target` : `echo x>../f`, `echo x 2>../f`, `echo x 1>../f`,
      `echo x &>../f` et `echo x >|../f` rendent la cible `../f`
- [x] `test_every_tee_argument_is_a_target` : `tee a ../b` rend `a` et `../b`
- [x] `test_cp_mv_rm_targets_outside_the_root_are_refused` : `cp x ../y`, `mv x ../y`,
      `rm -r ../autre` sont refusés hors de la racine, et passent dedans
- [x] `test_windows_backslash_path_is_not_eaten` : `echo x > ..\f` rend `..\f`
## Fin à la main (04/11)

L'audit sécurité a bloqué le run sur un faux positif : il voyait une `ValueError` au
déballage du tuple de `_lire_arguments` (ligne 122) et affirmait que « tous les tests sur
cp/mv/rm échouent », alors que le testeur venait de rendre la suite verte. Relu à la main
(couverture élargie, rien d'affaibli : une ligne illisible ne rend toujours aucune cible) ;
59 tests de redirection et de périmètre verts, mypy propre.
