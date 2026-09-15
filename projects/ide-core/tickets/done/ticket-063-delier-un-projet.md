---
id: ticket-063
title: "Retirer un projet de l'IDE sans le supprimer"
type: feat
status: done
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

- [x] Retirer un projet le fait disparaître de l'IDE sans perte de fichiers
- [x] Retirer un projet lié en `symlink` supprime le lien, jamais la cible
- [x] Retirer un projet `copy`/`clone` déplace le dossier et dit où
- [x] La suppression définitive est une action distincte, avec confirmation
- [x] La confirmation nomme le chemin réel et les commits non poussés
- [x] La suppression définitive d'un `symlink` ne touche jamais la cible
- [x] L'historique de pipelines du projet en base est conservé ou purgé
      explicitement, pas laissé orphelin

## Dépendances

Aucune.

## Estimation

**1j**.

## Risques

- **Élevé si mal fait** — c'est une fonctionnalité de suppression de fichiers
  de l'utilisateur. La règle : le chemin est résolu et affiché avant toute
  action, et aucune suppression ne franchit un lien symbolique.

## Livré

`services/project_removal.py` — `describe_removal`, `detach_project`,
`delete_project`. Endpoints `GET /removal-plan`, `POST /detach`,
`DELETE /{id}?confirmed=true`. `RemoveProjectModal` côté UI.

### La règle qui ne souffre aucune exception

**Aucune suppression ne franchit un lien symbolique.** `projects/fluentdb`
*est* `Desktop/fluentdb` : effacer le dossier de travail de l'utilisateur
depuis un IDE n'est jamais la bonne réponse. Deux tests le verrouillent, un
pour chaque action.

### Ce que la modale montre avant de décider

Le **chemin réellement visé**, liens résolus — jamais l'identifiant seul. Le
nombre de commits non poussés, qui est exactement ce qui serait perdu. Et pour
un lien, la mention explicite que son contenu ne sera pas touché.

La suppression définitive demande **deux** clics : le premier déplie la
confirmation, le second agit.

## Non traité

L'historique de pipelines du projet reste en base après retrait. Le purger
demanderait de décider ce qu'on fait d'un projet détaché puis réattaché : à
traiter si le cas se présente.
