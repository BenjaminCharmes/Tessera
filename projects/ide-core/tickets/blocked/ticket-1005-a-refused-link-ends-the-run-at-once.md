---
agent: codeur
depends_on:
- ticket-996
id: ticket-1005
preuve_reelle: true
priority: high
status: blocked
title: A refused link ends the run at once, named, instead of being read as an empty
  diff
type: fix
---

## Signalement

Preuve réelle du ticket-996, le 18/11 (Serpent ticket-010, run `fdaf5d74`) :
une jonction `docs/lien-996` créée dans le worktree du run, vers un dossier
du profil de l'utilisateur, juste après le démarrage du codeur.

Ce qui tient : rien n'est indexé, le fichier témoin derrière la jonction
n'entre dans aucun commit et n'est pas effacé, la jonction est retirée en fin
de run, le run finit `blocked` et le worktree est conservé.

Ce qui ne va pas :
- `pipeline_production._capture_diff` attrape `GitWorkspaceError`, dont
  hérite `LienNonDeclare` : `diff_failed`, diff vide, puis **prose du codeur**
  donnée à l'audit, au reviewer et au validateur. L'audit a rendu PASS et le
  validateur APPROVED sur ce texte. Seule la garde du diff vide (« Aucun
  fichier modifié : rien à approuver ») a refusé, et le run a enchaîné un
  second tour complet, tests et audit compris, pour rien.
- `pipeline_testeur._diff_du_run` avale la même erreur
  (`diff_du_testeur_illisible`).
- L'arrêt final ne nomme pas le lien : `stopped_by_user` puis
  `commit_failed`, sans commit (`commit_sha: null`), alors qu'ADR-037 veut
  un run `blocked` **avec** commit.

## Ce qu'il faut faire

- `LienNonDeclare` levée en lisant le diff (production, testeur) termine le
  run tout de suite en `blocked`, sans autre appel d'agent. L'arrêt nomme le
  ou les liens.
- Avant le commit de fin, les liens refusés se retirent (comme
  `retirer_les_liens` le fait déjà pour ceux de `populate`, sans suppression
  récursive) ; le travail se commite alors comme un run non approuvé
  (ADR-037). Un lien qui ne se retire pas laisse le worktree en place, comme
  aujourd'hui.
- Les autres `GitWorkspaceError` gardent le comportement actuel.

## Critères d'acceptation

- [ ] Test : un lien non déclaré dans l'arbre après le codeur → run
  `blocked` au tour 1, aucun appel d'audit, de reviewer ni de validateur,
  arrêt qui contient le chemin du lien.
- [ ] Test : même cas → un commit « unapproved work » existe sur la branche,
  sans la cible du lien, et la cible est intacte.
- [ ] Test : le testeur ne relance aucun test quand le diff lève
  `LienNonDeclare` ; l'erreur remonte.

## Preuve réelle

Relancer la même expérience sur un run Serpent : jonction créée dans le
worktree après le démarrage du codeur → `blocked` au tour 1, lien nommé dans
l'arrêt, commit non approuvé sans la cible.

## Ce que ça ne fait pas

- Ne change pas la règle du 996 (ce qui est un lien admis).
- Ne revoit pas le repli sur la prose pour les autres échecs de diff.