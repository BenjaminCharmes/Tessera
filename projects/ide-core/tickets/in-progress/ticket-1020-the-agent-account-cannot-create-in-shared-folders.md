---
id: ticket-1020
title: "The agent account cannot create files in shared folders"
type: feat
status: in-progress
priority: medium
agent: codeur
preuve_reelle: true
---

# ticket-1020 — Le compte agent ne crée plus rien dans les dossiers partagés

## Objectif

ADR-088, point 3. Le compte agent est membre du groupe des utilisateurs : il
crée des fichiers dans les dossiers ouverts à tout utilisateur, que le
nettoyage du profil (ticket-1008) ne touche pas.

## Ce qui a changé depuis la première fiche

La première fiche prévoyait une purge par le backend. Essai du 19/11 sous le
compte, dans un appel réel :

| Dossier | Le compte y crée un fichier | Le backend le supprime |
|---|---|---|
| Dossier public des utilisateurs, et son sous-dossier Documents | oui | oui |
| Dossier temporaire de Windows | oui | non : le backend ne peut même pas le lire |
| Racine du dossier des données de programmes | oui | non : accès refusé |
| Racine du lecteur, dossier partagé de Tessera | non | sans objet |

La purge est donc impossible sans administrateur. L'utilisateur a tranché le
19/11 : refuser la création, par un script qu'il lance une fois en
administrateur.

## Ce qui est fait

- `scripts/agent-refus-creation-admin.ps1` pose, pour le seul compte agent
  (visé par son SID), un refus « créer un fichier, créer un dossier » sur les
  trois dossiers, hérité par leurs sous-dossiers. `-Retirer` le défait.
- Il ne touche ni au compte, ni à son mot de passe, ni à son jeton, ni aux
  droits d'un autre compte. Le dossier partagé de Tessera a son héritage
  coupé : worktrees, outils et profil du compte ne reçoivent rien.
- Essayé le 20/11 sur un dossier jetable, sans élévation : pose, relance
  (rien ne change), héritage par un sous-dossier, sous-dossier à héritage
  coupé épargné, retrait, dossier absent (rien n'est posé). Le premier essai
  a montré qu'`icacls` doublait l'entrée à la relance : un dossier déjà dans
  l'état voulu est désormais sauté.

## Critères d'acceptation

- [ ] Le script ne contient qu'un `/deny`, visé par SID, sur `(CI)(WD,AD)`, et
  aucun `/grant`, `/inheritance`, `/setowner` ni commande de compte (test).
- [ ] Les trois dossiers sont nommés ; tous sont vérifiés avant le premier
  changement (test).
- [ ] `-Retirer` retire le refus ; un dossier déjà dans l'état voulu est sauté
  (test).
- [ ] `docs/agent-isolation.md` dit comment le lancer et le défaire (test).

## Preuve réelle

Sur le poste, hors dépôt, hors run :

1. L'utilisateur lance le script une fois en administrateur.
2. Sous le compte (`lancer_sous_compte`), tenter de créer un fichier dans
   chacun des trois dossiers et dans le sous-dossier Documents du dossier
   public : chaque tentative est refusée.
3. Un run complet de Serpent va au bout : rien de ce dont le compte a besoin
   ne passe par ces dossiers.

## Ce que ça ne fait pas

- Ne retire pas le compte du groupe des utilisateurs.
- N'atteint pas un sous-dossier dont l'héritage est coupé, ni un sous-dossier
  qui accorde en propre la création aux utilisateurs : une autorisation propre
  passe avant un refus hérité.
- Ne supprime pas un fichier que le compte y aurait déjà laissé.
- Le backend ne vérifie pas que le refus est en place : il ne peut pas lire
  les droits du dossier temporaire de Windows.
