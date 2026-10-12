---
agent: codeur
created: 2026-10-12
depends_on: []
estimated_days: 0.5
id: ticket-402
pr_number: null
priority: medium
status: todo
title: Doc edits find their anchor text despite typographic punctuation and non-breaking
  spaces
type: fix
---

# ticket-402 — Les éditions de doc retrouvent leur texte malgré la typographie

## Objectif

Qu'une édition de doc qui cite un passage avec une apostrophe droite, des
guillemets droits ou des espaces normales retrouve ce passage même quand le
fichier utilise la typographie française.

## Contexte

`_remplacer` et `_inserer` (`backend/src/tessera/services/documentation.py`)
cherchent le texte `ancien`, ou le titre `apres_section`, à l'identique. Le
ticket-395 tolère la casse et les espaces, mais seulement dans les titres.

Signalé par la session qui pilote affut le 2026-10-12 à 08:24 UTC
(ticket-021) : « documentation: 0 fichier(s) — après tour de correction —
refusé ». Le README contient `L’application` (U+2019), alors que l'agent
cite `L'application` (U+0027). Même le tour de correction ne peut pas
aboutir : l'agent ne voit pas la différence.

## Solution proposée

1. Une fonction `_normaliser_typo(texte)` remplace :
   - ’ et ‘ par ' ;
   - “, ”, « et » par " ;
   - … par ... ;
   - les espaces insécables U+00A0 et U+202F par une espace.
   Elle rend aussi, pour chaque caractère du texte normalisé, sa position
   dans le texte d'origine.
2. `_remplacer` cherche d'abord le texte exact. Faute de correspondance, il
   cherche `_normaliser_typo(ancien)` dans `_normaliser_typo(avant)`. Une
   correspondance unique est remplacée **aux positions du texte
   d'origine**, et le reste du fichier garde sa typographie. Plusieurs
   correspondances : refus, comme aujourd'hui.
3. `_inserer` applique la même normalisation aux titres, en plus de celle du
   ticket-395.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_documentation.py` vérifie qu'un `ancien` « L'application suit » remplace « L’application suit » dans un fichier qui l'écrit avec U+2019, et que le reste du fichier garde ses apostrophes typographiques
- [ ] Un test de `backend/tests/test_documentation.py` vérifie qu'un `ancien` avec des guillemets droits et une espace normale retrouve un passage écrit « ainsi » avec des espaces insécables
- [ ] Un test de `backend/tests/test_documentation.py` vérifie qu'un `ancien` qui correspond à deux passages après normalisation est refusé
- [ ] Un test de `backend/tests/test_documentation.py` vérifie que la correspondance exacte reste prioritaire quand elle existe

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Ce que ça ne fait pas

- Ne réécrit pas la typographie des fichiers de doc.