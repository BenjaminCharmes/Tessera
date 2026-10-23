---
agent: codeur
created: 2026-10-23
depends_on:
- ticket-541
id: ticket-542
priority: high
status: done
title: A documentation edit must quote the code that supports it
type: feat
---

## Objectif

Rendre mécanique le contrôle des faits : chaque édition cite le code livré qui
la fonde, et les nombres, ADR et noms qu'elle introduit doivent s'y trouver
(ADR-057, section « Preuve » du spec).

## Critères d'acceptation

- [ ] `appliquer_editions` reçoit la matière fournie à l'agent (tickets, diff, fichiers) et refuse, avec `EditionRefusee`, une édition sans `preuve` ou à `preuve` vide, sauf une édition dont `nouveau` est vide (retrait)
- [ ] Un `extrait` de la preuve absent de la matière est refusé ; la comparaison tolère la typographie (`_normaliser_typo`), test à l'appui avec une apostrophe et une espace insécable
- [ ] Un jeton vérifiable présent dans `nouveau` ou `texte`, absent de `ancien` et de la matière, fait refuser l'édition. Jetons : `ADR-N`, `ticket-N`, nombre suivi d'une unité, numéro de migration, extension en capitales, mot entre guillemets. Un test par famille, dont `ADR-019` face à une matière qui ne porte que `ADR-018` et `10 Mo` face à `5 Mo`
- [ ] La matière du contrôle ne contient pas la documentation actuelle : un jeton présent seulement dans la doc existante est refusé
- [ ] Une édition `ancien`/`nouveau` qui remplace plus de 2 000 caractères est refusée, et un rôle ne remplace pas plus de 8 000 caractères sur un lot ; les deux sont des constantes nommées. Une création (`contenu`) est exempte du volume, pas de la preuve
- [ ] Le motif du refus nomme la règle enfreinte et rejoint le tour de correction du ticket-395, qui reçoit aussi la liste des fichiers de la matière
- [ ] Les deux prompts décrivent le format `preuve: [{fichier, extrait}]` avec un exemple, et la règle de volume
- [ ] Un test montre le cas du 22/10 : une édition de guide citant un diff d'en-têtes de sécurité pour réécrire un passage sur le compte est refusée faute d'extrait qui le soutient

## Ce que ça ne fait pas

- Ne juge pas qu'un extrait existant soutient la phrase : le spec le dit comme limite connue.
- Ne change ni le lot, ni le brief : 541.