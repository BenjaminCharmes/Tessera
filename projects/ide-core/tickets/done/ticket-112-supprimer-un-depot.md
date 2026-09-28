---
id: ticket-112
title: "Supprimer un projet qui contient un dépôt git"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-104"]
estimated_days: 1
created: 2026-09-21
---

# ticket-112 — Supprimer un projet qui contient un dépôt git

## Objectif

Que la suppression d'un projet fonctionne sous Windows, maintenant que tout
projet créé porte un dépôt git.

## Contexte

`DELETE /api/v1/projects/{id}?confirmed=true` rend un **500** :

```
PermissionError: [WinError 5] Accès refusé:
  '…\essai-jetable\.git\objects\00\07d9e3246b0bdfb0a9dcebd8056df271077a65'
```

Git marque ses objets en **lecture seule**. Sous Windows, `shutil.rmtree`
refuse d'effacer un fichier portant cet attribut, là où POSIX ne regarde que
les droits du dossier parent. La suppression casse donc sur l'objet git, pas
sur le projet.

C'est une conséquence directe du ticket-104, et elle n'avait pas été
anticipée : avant lui, un projet créé n'avait **pas** de `.git`, et la
suppression fonctionnait. En donnant un dépôt à chaque projet, on a cassé
l'opération inverse.

Le défaut a été trouvé en créant un vrai projet depuis l'API, pas par les
tests : ceux-ci suppriment des dossiers sans dépôt.

**Aggravation** : `rmtree` efface au fil de son parcours. Un échec survenant
plus tard laisserait un dépôt à moitié supprimé — un projet ni effacé, ni
utilisable. Ici l'échec est tombé tôt et `git fsck` est resté vert, mais c'est
une chance, pas une garantie.

## Solution proposée

Passer un gestionnaire d'erreur à `rmtree` qui retire l'attribut lecture seule
et réessaie une fois. C'est le remède habituel pour ce cas, et il ne change
rien sur POSIX, où l'erreur ne se produit pas.

Le gestionnaire ne doit **pas** avaler les autres erreurs : un fichier
verrouillé par un autre processus doit toujours remonter, sinon la suppression
se déclarerait réussie en laissant des fichiers.

## Critères d'acceptation

- [ ] Un test crée un projet contenant un fichier en **lecture seule** sous
      `.git/objects/`, le supprime, et vérifie que le dossier a disparu
- [ ] Ce test échoue sans le correctif, sur Windows
- [ ] Une erreur qui n'est pas un problème de droits remonte toujours : la
      suppression ne se déclare pas réussie à tort
- [ ] `DELETE /api/v1/projects/{id}?confirmed=true` rend 204 sur un projet
      créé par l'IDE
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

Ne rend pas la suppression atomique. Si elle échoue au milieu pour une autre
raison, le projet reste partiel — le rendre transactionnel demanderait de
copier avant d'effacer, ce qui est disproportionné ici.

## Dépendances

ticket-104, qui a donné un dépôt à chaque projet créé.

## Estimation

1 jour.

## Risques

Retirer un attribut de fichier avant de l'effacer est une opération que le
correctif applique à tout ce qu'il supprime. Le périmètre reste borné par les
gardes déjà en place : la suppression refuse déjà tout chemin qui n'est pas une
entrée directe du workspace, et s'arrête aux liens symboliques.
