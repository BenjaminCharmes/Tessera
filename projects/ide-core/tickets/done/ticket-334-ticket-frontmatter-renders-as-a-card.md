---
id: ticket-334
title: "The YAML header of a Markdown file renders as a field card instead of a garbled paragraph"
type: fix
status: done
pr_number: 251
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-334 — L'en-tête YAML d'un Markdown s'affiche en fiche

## Objectif

Que la vue « Rendu » d'un ticket affiche son en-tête lisiblement.

## Contexte

Retour de l'utilisateur le 2026-10-05 : le haut des tickets s'affiche mal.
`marked` ne connaît pas le frontmatter : le `---` d'ouverture devient une
règle horizontale, tous les champs un seul paragraphe
(« agent: codeur created: 2026-10-02 depends_on: [] … »), le `---` de
fermeture un titre. La vue « Source » (Monaco) l'affiche correctement.

## Solution proposée

Séparer l'en-tête du corps avant `marked` (un champ `clé: valeur` par ligne,
une ligne indentée prolonge la valeur précédente), et l'afficher en fiche
clé/valeur au-dessus du corps rendu. Les valeurs passent par React, jamais
par le HTML injecté.

## Critères d'acceptation

- [x] Un test vérifie que `separerFrontmatter` rend un champ par clé et le
      corps sans l'en-tête
- [x] Un test vérifie qu'une valeur repliée sur deux lignes est rejointe, et
      qu'un fichier en CRLF est lu
- [x] Un test vérifie qu'un fichier sans en-tête, même avec un `---` plus
      bas, reste intact
- [x] Un test rend `MarkdownView` sur un ticket et vérifie la fiche, sans
      `<hr>` ni paragraphe « id: … »

## Dépendances

Aucune.

## Estimation

0,5 jour.
