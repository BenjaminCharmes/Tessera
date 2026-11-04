---
id: ticket-785
title: "The design-ui skill names its motion and micro-interaction rules"
type: docs
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-785 — Le skill design-ui nomme ses règles de mouvement et de micro-interactions

## Objectif

Le codeur et l'architecte ont des règles concrètes et chiffrées pour animer une interface, au
lieu d'une seule ligne (« une animation accompagne un changement d'état »).

## Contexte

Revue d'outils du 04/11 : trois dépôts de skills de design ont été lus sans rien installer
(règle du 30/10 : reprendre les idées). Tous sous licence MIT.
- emil-design-eng (Emil Kowalski) : Markdown seul, aucun script ; règles chiffrées sur le
  mouvement. Retenu.
- taste-skill : scripts Node et d'installation, orienté sites vitrines ; ses règles d'écran
  d'application recoupent déjà la charte. Rien de neuf.
- ui-ux-pro-max : moteur Python et CLI npm ; conseils de mouvement qualitatifs, couverts
  par le premier. Rien de neuf.

## Solution

Faite à la main : une section « Mouvement et micro-interactions » dans
`agents/plugin/skills/design-ui/SKILL.md` — selon la fréquence de l'action, propriétés
animées, courbes, durées, interruption, retour d'appui, survol réservé aux pointeurs précis,
mouvement réduit livré avec l'animation. La relecture finale (§8) repasse ces règles.

## Critères d'acceptation

- [x] `agents/plugin/skills/design-ui/SKILL.md` porte une section « Mouvement et
      micro-interactions » avec des durées chiffrées et la règle du mouvement réduit
- [x] La relecture finale du skill renvoie à cette section
