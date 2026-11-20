---
id: ticket-1020
title: "Files of the agent account in shared folders are purged"
type: feat
status: blocked
priority: medium
agent: codeur
preuve_reelle: true
---

# ticket-1020 — Les fichiers du compte dans les dossiers partagés se purgent

## Objectif

ADR-088, point 3. Le compte agent est membre du groupe des utilisateurs : il
crée des fichiers dans les dossiers ouverts à tout utilisateur, que le
nettoyage du profil (ticket-1008) ne touche pas.

## Essais faits le 19/11, avant de coder : le ticket est à redéfinir

Sous le compte, dans un appel réel :

| Dossier | Le compte y crée un fichier | Le backend le supprime |
|---|---|---|
| Dossier public des utilisateurs, et son sous-dossier Documents | oui | oui |
| Dossier temporaire de Windows | oui | non : le backend ne peut même pas le lire |
| Racine du dossier des données de programmes | oui | non : accès refusé |
| Racine du lecteur, dossier partagé de Tessera | non | sans objet |

La purge par le backend, non administrateur, ne couvre donc que le dossier
public. Ailleurs, « un fichier que le backend ne peut pas supprimer lève
`DroitsAgentRefuses` » bloquerait chaque run sur un simple fichier posé par
un agent, sans que personne ne puisse le retirer sans droit
d'administrateur.

Deux issues, à trancher par l'utilisateur :

1. **Refuser la création** : `agent-setup-admin.ps1` pose, une fois, un refus
   de création pour le compte sur ces dossiers. L'ADR-088 l'a écarté
   (modifier l'ACL d'un dossier système) ; c'est pourtant la seule fermeture
   réelle.
2. **Accepter** : un fichier laissé là n'atteint ni un worktree ni un secret,
   et rien ne l'exécute. Le noter dans l'ADR-088 et annuler ce ticket.

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
