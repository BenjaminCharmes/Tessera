---
agent: codeur
created: 2026-11-20
depends_on: []
estimated_days: 1
id: ticket-1034
priority: medium
status: done
title: A weekly ritual turns the radar into tickets
type: chore
---

# ticket-1034 — Un rituel hebdomadaire change le radar en tickets

## Signalement

- Projet source : tous (idée du 16/11, gardée pour après la stabilisation)
- Le radar de Vigie propose chaque semaine des tickets candidats par projet.
  Personne ne les confronte au dépôt : le 16/11, il proposait à un projet une
  montée de version déjà en ligne.

## Ce qui est fait

Fait à la main, sans run : ni code ni test nouveau.

- `.claude/skills/radar-hebdo/SKILL.md` : lire les exports
  (`projects/vigie/exports/radar-<projet>.md`, `veille/<semaine>.json`),
  confronter chaque candidat au dépôt (version installée, tickets existants,
  critères vérifiés dans le code), écrire les seuls tickets qui tiennent, une
  PR de fiches par projet, aucune file lancée, un récapitulatif avec la raison
  de chaque candidat écarté.
- `rituels.md` : le rituel `radar-hebdo`, le lundi à 09:30 ; la table du
  format dit aussi le rythme `quotidien` (ticket-1033).
- `CLAUDE.md` : `radar-hebdo` entre dans la liste des skills disponibles. Ce
  ticket autorise cette modification, et elle seule.

## Critères d'acceptation

- [x] `test_les_skills_annonces_existent` passe avec le nouveau skill.
- [x] `rituels.md` se lit sans erreur avec le rituel ajouté
      (`lire_definitions`).
- [x] `test_consignes_coherentes.py` passe.

## Ce que ça ne fait pas

- N'automatise rien : c'est un rituel, lancé par une phrase.
- Ne modifie ni Vigie ni ses exports, écrits sur le PC et ignorés par git.
- Ne lance aucune file : la session du projet décide du moment.
