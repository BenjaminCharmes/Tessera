---
id: ticket-541
title: "The documentation batch reads the delivered code, oldest tickets first"
type: feat
status: todo
priority: high
agent: codeur
depends_on:
- ticket-540
created: 2026-10-23
---

## Objectif

Brancher la matière de 540 sur le lot de documentation, et mettre les prompts
en accord avec ce que les agents reçoivent (ADR-057).

## Critères d'acceptation

- [ ] `_brief` reçoit les tickets, puis le diff de chaque ticket, puis les fichiers touchés, puis la documentation actuelle, dans cet ordre ; un test sur `_brief` vérifie la présence et l'ordre des quatre blocs
- [ ] `_PLAFOND` vaut 5 et le lot garde les **plus anciens** tickets : avec sept tickets en attente, les cinq premiers sont documentés et les deux derniers restent hors du marqueur, test à l'appui
- [ ] Les tickets sans diff retrouvable sont retirés du lot, marqués documentés, et le journal du pipeline écrit une ligne par ticket (« pas de diff retrouvable, non documenté ») ; un lot qui n'a plus aucun ticket n'appelle aucun agent
- [ ] `ResultatDocumentation` porte les tickets écartés, et l'événement de fin de documentation les liste
- [ ] `agents/prompts/doc-technique.md` et `agents/prompts/doc-fonctionnelle.md` ne disent plus « Pas les diffs » ni « N'invente rien qui ne soit pas dans les tickets » ; ils décrivent les quatre blocs reçus, disent qu'un fait absent du diff et des fichiers n'est pas à écrire, et qu'un ticket sans effet pour le lecteur donne `{"editions": []}`
- [ ] Les tests existants de `test_documentation.py` et `test_consignes_coherentes.py` sont adaptés, aucun supprimé sans remplaçant

## Ce que ça ne fait pas

- Ne vérifie pas encore les preuves ni le volume des éditions : 542.
- Ne règle pas les conflits de documentation entre PR d'une file : 533.
- Ne change pas le modèle : 543.
