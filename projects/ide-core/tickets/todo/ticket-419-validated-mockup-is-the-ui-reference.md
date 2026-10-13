---
id: ticket-419
title: "A validated mockup in design/maquette becomes the UI reference the coder reproduces, for every project"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-13
---

# ticket-419 — Une maquette validée devient la référence d'interface

## Objectif

Généraliser ce qui a marché sur `curio` : quand un projet porte une maquette
validée, chaque agent qui touche à l'interface la reproduit au lieu
d'inventer.

## Contexte

Le 2026-10-13, Curio a été lancé avec une maquette faite avec Benjamin dans
l'éditeur de maquettes de Claude (quatre écrans téléphone), versionnée dans
`design/maquette/*.dc.html`, et une charte `memory/design.md` qui en est
tirée. Les écrans livrés par le pipeline (tickets 005 à 008) sont fidèles à
la maquette dès le premier tour, alors que plusieurs projets précédents
avaient dû refaire leur interface (refonte de freelance, chartes écrites à
l'aveugle). Rien dans Tessera ne connaît encore cette étape : c'est
`curio/CLAUDE.md` et `design/maquette/README.md` qui l'ont portée.

## Solution proposée

- `agents/plugin/skills/design-ui/SKILL.md` : une section « 0. Maquette
  d'abord », avant « Charte d'abord » : si `design/maquette/` existe, elle
  fait foi pour la structure, l'ordre des blocs, les tailles, les espacements
  et les états ; chaque couleur en dur de la maquette devient le token
  correspondant de la charte ; les textes d'exemple sont des données, pas du
  contenu à recopier ; les fichiers `.dc.html` se lisent comme du HTML à
  styles en ligne (balises `<x-dc>`, `<sc-for>`, `<sc-if>`, `{{ valeur }}`
  propres à l'éditeur).
- `templates/fastapi-react/design/maquette/README.md` : le mode d'emploi
  (d'où vient une maquette, comment la lire, ce qui fait foi), repris de
  celui de curio, pour qu'un projet créé depuis le gabarit ait la place
  prête.

## Critères d'acceptation

- [ ] `agents/plugin/skills/design-ui/SKILL.md` contient une section
      « Maquette d'abord » placée avant « Charte d'abord », qui cite
      `design/maquette/`
- [ ] `templates/fastapi-react/design/maquette/README.md` existe et explique
      que la structure fait foi et que les couleurs deviennent des tokens
- [ ] Un test de `project_from_template` vérifie que le projet créé contient
      `design/maquette/README.md`

## Dépendances

Aucune.

## Ce que ça ne fait pas

- La maquette elle-même se fait avec Benjamin, hors pipeline : un agent du
  produit n'a pas accès aux artifacts claude.ai.
