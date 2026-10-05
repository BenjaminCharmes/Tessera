---
id: ticket-338
title: "The design-ui skill makes every charter declare its color-scheme and style its scrollbars"
type: docs
status: in-progress
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.25
created: 2026-10-05
---

# ticket-338 — `design-ui` impose `color-scheme` et des scrollbars aux tokens

## Objectif

Une app construite par Tessera ne laisse plus le navigateur peindre ses widgets
natifs (scrollbars, champs, menus `select`) dans un thème qui n'est pas le sien.

## Contexte

Tessera déclare `:root { color-scheme: dark; }` et des scrollbars aux couleurs
de sa charte (`frontend/src/index.css`). Aucun projet géré ne le fait :
`carriere` et `demineur` sont sombres, et leurs scrollbars s'affichent en
blanc. Le défaut revient à chaque nouveau projet, parce que le skill
`design-ui`, que reçoivent le codeur et l'architecte, n'en dit rien.

Sans `color-scheme`, le navigateur ne déduit pas le thème des couleurs CSS. Il
suit sa propre préférence. Une app sombre sur un navigateur clair a donc des
widgets blancs. Une app claire sur un navigateur sombre a des widgets noirs.
Le thème déclaré doit suivre **la charte**, pas le système.

## Solution proposée

Ajouter au skill (`agents/plugin/skills/design-ui/SKILL.md`) une section
« Thème du navigateur » :

- la charte déclare `color-scheme` à la valeur de son thème, une seule ;
- une charte à deux thèmes bascule `color-scheme` avec sa classe ou sa media
  query ;
- les scrollbars (`scrollbar-color`, `::-webkit-scrollbar-*`) prennent leurs
  couleurs dans les tokens de surface et de bordure, pas dans l'accent.

## Critères d'acceptation

- [ ] `design-ui/SKILL.md` contient une section qui impose `color-scheme` à la
      valeur du thème de la charte
- [ ] La section dit que les couleurs des scrollbars viennent des tokens de
      surface et de bordure
- [ ] Le point 1 du skill (« ce que contient la charte ») liste le thème déclaré

## Ce que ça ne fait pas

- Ne corrige pas les projets existants : un ticket par projet
  (`carriere` ticket-057, à suivre pour `demineur` et `portfolio`).
