---
id: ticket-109
title: "Deux tests ne passaient que sur le poste de leur auteur"
type: fix
status: done
pr_number: 122
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-21
---

# ticket-109 — Deux tests ne passaient que sur le poste de leur auteur

## Objectif

Que la suite backend passe ailleurs que sur la machine qui l'a écrite.

## Contexte

Le dépôt est passé public, donc la CI tourne de nouveau — pour la première
fois depuis le 18 septembre. Elle a immédiatement trouvé deux échecs que la
vérification locale ne pouvait pas voir, parce que les deux tests **dépendent
de fichiers non versionnés** :

1. `test_l_arborescence_decrite_existe` exige que tout fichier `.json` décrit
   dans `CLAUDE.md` existe. Or `CLAUDE.md` décrit `settings.local.json` en le
   marquant lui-même **« (gitignoré) »**. Le test exige donc la présence d'un
   fichier que le dépôt s'interdit de versionner.

2. `test_un_prompt_branche_par_un_projet_parle_dans_le_pipeline` vérifie que
   `analyste-carriere` a le moment `pipeline`. Ce moment se calcule à partir
   des `agents.json` des projets réellement présents dans `projects/`. Seul
   `ide-core` est versionné : ailleurs, aucun projet ne branche cet agent, et
   son moment est `jamais`.

C'est le défaut que `test_consignes_coherentes.py` existe pour empêcher, pris
par l'autre bout : le fichier vérifiait que les consignes ne mentent pas, et
mentait lui-même sur ce qu'un clone neuf contient.

## Solution proposée

1. Exempter de la vérification les fichiers que `CLAUDE.md` annonce
   gitignorés. Le marqueur est déjà dans le texte : il suffit de le lire.
2. Réécrire le second test pour construire son propre projet, dans un
   `tmp_path`, avec un `agents.json` qui branche le prompt. Il vérifie alors
   le **mécanisme** — un projet peut substituer un prompt — au lieu de
   constater une configuration locale.

## Critères d'acceptation

- [ ] `test_l_arborescence_decrite_existe` passe sur un clone ne contenant
      aucun fichier gitignoré
- [ ] Un fichier décrit dans `CLAUDE.md` **sans** mention de gitignore et
      réellement absent fait toujours échouer le test
- [ ] `test_un_prompt_branche_par_un_projet_parle_dans_le_pipeline` ne lit plus
      le dossier `projects/` du dépôt
- [ ] Le test échoue si le mécanisme de substitution cesse de fonctionner
- [ ] `uv run pytest` est vert, et **la CI GitHub l'est aussi**

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Exempter trop largement viderait le test de son sens : seule la mention
explicite de gitignore, dans la ligne qui décrit le fichier, ouvre
l'exemption. Un fichier simplement absent reste une erreur.
