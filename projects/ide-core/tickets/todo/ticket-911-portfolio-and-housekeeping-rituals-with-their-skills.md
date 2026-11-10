---
agent: codeur
created: 2026-11-10
depends_on: ["ticket-910", "ticket-913"]
estimated_days: 0.5
id: ticket-911
pr_number: null
priority: medium
status: todo
title: Portfolio and housekeeping rituals, with the skills that run them
type: chore
---

# ticket-911 — Rituels « Portfolio » et « Ménage », et leurs skills

## Objectif

Une mise à jour hebdomadaire du portfolio et un ménage mensuel des fichiers
de mémoire, chacun déclenché par un rituel et mené par un skill.

## Contexte

Les rituels (tickets 902 à 908) rappellent ce qui revient. Les relevés des
tickets 910 et 913 donnent les faits ; il manque la consigne de la session
qui les exploite, et l'entrée dans `rituels.md`.

**Ce ticket se fait à la main** : ses livrables vivent dans `.claude/skills/`,
qu'aucun agent ne peut écrire.

## Solution proposée

- `rituels.md` : deux entrées.
  - `portfolio-hebdo` : vendredi 17:00, 45 min, phrase « portfolio hebdo »,
    projets `[portfolio]`.
  - `menage-mensuel` : le 1er du mois, 10:00, 30 min, phrase « ménage »,
    projets `[ide-core]`.
- Skill `portfolio-hebdo` : lancer le relevé de la semaine (ticket-910),
  lire les faits notables, mettre à jour les pages projets du portfolio, et
  proposer un article **seulement si la semaine a un vrai sujet**. Tout passe
  par une PR du portfolio, les articles en `draft: true`. Chaque chiffre cite
  sa source ; `memory/style-redaction.md` du portfolio s'applique ; jamais
  pendant une file ; rien de professionnel.
- Skill `menage-mensuel` : lancer le relevé de ménage (ticket-913), proposer
  le tri dans une PR (archiver, fusionner, raccourcir), jamais une
  suppression sans accord.
- `CLAUDE.md` racine : ajouter les deux skills à la liste « Skills
  disponibles ». **Ce ticket autorise cette modification de `CLAUDE.md`.**

## Critères d'acceptation

- [ ] `rituels.md` déclare `portfolio-hebdo` et `menage-mensuel` avec les
      rythmes ci-dessus, et la vue Rituels les affiche.
- [ ] `.claude/skills/portfolio-hebdo/SKILL.md` et
      `.claude/skills/menage-mensuel/SKILL.md` existent.
- [ ] La liste des skills de `CLAUDE.md` les nomme, et
      `test_consignes_coherentes.py` passe.

## Dépendances

ticket-910, ticket-913.

## Estimation

Une demi-journée.

## Risques

Un article hebdomadaire imposé finirait en remplissage : le skill dit
explicitement qu'une semaine sans sujet n'en produit pas.
