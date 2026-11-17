---
agent: codeur
depends_on: []
id: ticket-996
preuve_reelle: true
priority: critical
status: done
title: A reparse point in the run tree blocks the run before any add or diff
type: fix
---

## Signalement

- Audit sans contexte du 17/11, constat C2 (CRITICAL). Bloque la release.

## Contexte

Tout compte Windows crée une jonction (`mklink /J`) sans privilège, vers un
dossier qu'il ne peut pas lire. Le backend, sous le compte de l'utilisateur,
la suit : `services/git_workspace/commits.py` (`commit_all`, `add -A`) et
`services/git_workspace/etat.py` (`add -A -N` puis `git diff`). L'auditeur a
vérifié avec git 2.53 : `git add -A` indexe `lien/secret.txt` et `git diff`
en affiche le contenu.

Scénario : l'agent crée `docs/x` → `C:\Users\<utilisateur>\.ssh` (ou le
checkout de Tessera et son `.env`). Le diff part au reviewer, à l'audit, au
validateur et aux journaux ; le commit fige ces fichiers sur la branche ; au
run suivant ils sont extraits en vrais fichiers lisibles par l'agent ; un run
approuvé les pousse.

`run_worktree_populate.retirer_les_liens` n'est appelé qu'à la suppression du
worktree et à la reprise au démarrage.

## Ce qu'il faut faire

- Avant tout `git add`, `git diff` ou calcul d'empreinte sur l'arbre d'un
  run, parcourir l'arbre (sans suivre de lien) et refuser tout point de
  reparse (jonction, lien symbolique, montage) qui n'est pas un lien posé par
  `populate` (ADR-056) : le run passe en `blocked`, le lien est nommé, rien
  n'est indexé (ADR-037).
- Les liens de `populate` sont exclus de l'index (`.git/info/exclude`) ; le
  vérifier, et refuser un lien de `populate` qui viserait hors de la cible
  déclarée.
- Même contrôle à la reprise au démarrage (`reprise_worktrees.py`), avant son
  `add --all`.

## Critères d'acceptation

- [ ] Test sur dépôt réel (Windows, jonction ; ailleurs, lien symbolique) :
      un lien créé dans l'arbre vers un dossier extérieur → `blocked`, l'index
      ne contient aucun fichier de la cible, le diff transmis aux portes non
      plus.
- [ ] Test : un lien de `populate` déclaré ne bloque pas.
- [ ] Test : la reprise au démarrage refuse de commiter un arbre qui porte un
      lien non déclaré.

## Ce que ça ne fait pas

- N'interdit pas à l'agent de lire hors du projet (ADR-031) : seul le backend
  cesse de suivre ses liens.