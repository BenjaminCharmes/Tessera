---
id: ticket-063
title: "Retirer un projet de l'IDE sans le supprimer"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-15
---

# ticket-063 — Retirer un projet de l'IDE

## Objectif

Pouvoir faire disparaître un projet de l'IDE sans perdre les fichiers.

## Contexte

L'IDE sait ajouter des projets de quatre façons et n'en sait retirer aucun. La
seule issue est de supprimer le dossier à la main dans le workspace — ce qui,
pour un projet importé en `symlink`, revient à peser sur un dossier de travail
réel.

Le danger tient au mode d'import, que rien ne rappelle au moment de retirer :

| Mode | Ce que contient le workspace | Conséquence d'une suppression |
|---|---|---|
| `symlink` | Un lien vers le dossier d'origine | Supprimer le lien est **sans risque** ; supprimer son contenu **détruit l'original** |
| `copy` | Une copie autonome | La supprimer perd le travail fait depuis l'import |
| `clone` | Un clone du dépôt distant | La supprimer perd les commits non poussés |

## Solution proposée

Deux actions distinctes, jamais confondues :

1. **Retirer** — le projet disparaît de l'IDE, les fichiers restent.
   - `symlink` : le lien est supprimé, la cible est intacte
   - `copy` / `clone` : le dossier est déplacé hors du workspace, dans un
     emplacement que l'UI indique
2. **Supprimer définitivement** — le dossier est effacé. Exige une confirmation
   qui **nomme ce qui sera perdu** : le chemin réel, et le nombre de commits
   non poussés s'il y en a.

Pour un `symlink`, « supprimer définitivement » ne doit **jamais** toucher à la
cible. Le proposer serait proposer d'effacer le dossier de travail de
l'utilisateur depuis un IDE.

## Critères d'acceptation

- [ ] Retirer un projet le fait disparaître de l'IDE sans perte de fichiers
- [ ] Retirer un projet lié en `symlink` supprime le lien, jamais la cible
- [ ] Retirer un projet `copy`/`clone` déplace le dossier et dit où
- [ ] La suppression définitive est une action distincte, avec confirmation
- [ ] La confirmation nomme le chemin réel et les commits non poussés
- [ ] La suppression définitive d'un `symlink` ne touche jamais la cible
- [ ] L'historique de pipelines du projet en base est conservé ou purgé
      explicitement, pas laissé orphelin

## Dépendances

Aucune.

## Estimation

**1j**.

## Risques

- **Élevé si mal fait** — c'est une fonctionnalité de suppression de fichiers
  de l'utilisateur. La règle : le chemin est résolu et affiché avant toute
  action, et aucune suppression ne franchit un lien symbolique.
