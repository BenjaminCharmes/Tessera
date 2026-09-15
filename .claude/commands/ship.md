---
description: Vérifie, commite, pousse et ouvre la PR vers develop pour le travail en cours
---

Termine le travail en cours : vérification, commits, push, PR.

1. Applique le skill `verification-before-completion` — lance réellement les
   commandes et lis leur sortie avant toute affirmation.
2. Applique le skill `ticket-workflow` — branche depuis `develop`, commits en
   anglais au format Conventional Commits, push, puis `gh pr create --base develop`.
3. Mets le fichier du ticket à jour : le dossier **et** le champ `status`.

N'annonce rien comme terminé sans la sortie des commandes à l'appui.
