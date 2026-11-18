---
agent: codeur
depends_on:
- ticket-1005
id: ticket-1011
preuve_reelle: false
priority: high
status: todo
title: A link found at the final commit is named, removed, and the work is committed
type: fix
---

## Signalement

Preuve réelle du ticket-1005, le 18/11 (Serpent ticket-010, run `474e2b69`) :
la jonction `docs/lien-1005` a été créée après la lecture du diff (pendant la
revue). Audit, reviewer et validateur ont approuvé le vrai diff, puis le
commit final a levé `LienNonDeclare` : `error commit_failed`, ticket
`blocked`, `commit_sha: null`, et un arrêt qui parle de « travail non
commité » sans nommer le lien. La cible est restée intacte et rien n'a été
indexé : la sécurité tient.

Le ticket-1005 ne traite que la lecture du diff (`lire_le_diff`,
`pipeline_lien_refuse.finish_lien_refuse`). Le commit de fin
(`pipeline_outcomes`, l. 113 et 137) passe encore par le chemin générique.

Vu aussi : un worktree conservé qui porte une jonction n'est pas repris
(« porte des changements non commités »). C'est juste, mais le motif ne
nomme pas le lien.

## Ce qu'il faut faire

- `LienNonDeclare` levée au commit de fin (approuvé ou non) passe par
  `finish_lien_refuse` : les liens refusés se retirent sans entrer dedans,
  le travail se commite en « unapproved work », et l'arrêt nomme le lien.
- Le refus de reprendre un worktree sale nomme les liens qu'il porte, quand
  il en porte.

## Critères d'acceptation

- [ ] Test (dépôt réel) : un lien créé après la lecture du diff et avant le
  commit de fin → run `blocked`, commit « unapproved work » sans la cible,
  arrêt qui contient le chemin du lien, cible intacte.
- [ ] Test : un worktree conservé qui porte un lien non suivi → le refus de
  reprise nomme le lien.

## Ce que ça ne fait pas

- Ne change pas la règle du 996 (ce qui est un lien admis).
- Ne reprend pas un worktree qui porte un lien : il reste refusé.
