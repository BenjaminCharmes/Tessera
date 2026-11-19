---
id: ticket-1020
title: "Files of the agent account in shared folders are purged"
type: feat
status: todo
priority: medium
agent: codeur
preuve_reelle: true
---

# ticket-1020 — Les fichiers du compte dans les dossiers partagés se purgent

## Objectif

ADR-088, point 3. Le compte agent est membre du groupe des utilisateurs : il
crée des fichiers dans les dossiers ouverts à tout utilisateur, que le
nettoyage du profil (ticket-1008) ne touche pas.

## Ce qu'il faut faire

- Une liste des dossiers à surveiller, déclarée dans un module de
  `services/providers/`, issue de l'inventaire ci-dessous (candidats :
  `C:\Users\Public`, `C:\Windows\Temp`, la racine de `C:\ProgramData`).
- À la clôture du dernier appel, juste après l'arrêt des restes du compte
  (`droits_appel.py`), parcourir ces dossiers sans suivre aucun lien : un
  fichier dont le propriétaire est le SID du compte se supprime.
- Un fichier que le backend ne peut pas supprimer lève `DroitsAgentRefuses` :
  le run finit `blocked` (ADR-037).
- Rien ne se refuse en écriture : modifier l'ACL d'un dossier système est
  écarté (ADR-088).

## Critères d'acceptation

- [ ] Un test : un fichier du compte dans un dossier de la liste est supprimé
  à la clôture ; un fichier d'un autre propriétaire reste.
- [ ] Un test : un lien (jonction) dans un dossier de la liste n'est pas suivi.
- [ ] Un test : un fichier non supprimable lève `DroitsAgentRefuses`.

## Preuve réelle

Sur le poste, hors dépôt :

1. **Avant de coder** : sous le compte, tenter de créer un fichier dans chaque
   dossier partagé courant (`Public`, `Windows\Temp`, `ProgramData`, racine
   des lecteurs) ; noter où cela aboutit et le propriétaire résultant.
2. Après le code : créer un fichier sous le compte dans chacun, terminer un
   appel, constater la suppression.

## Ce que ça ne fait pas

- Ne ferme pas la création (accepté : un fichier d'un autre dossier n'atteint
  ni un worktree ni un secret). Ne retire pas le compte du groupe des
  utilisateurs.
