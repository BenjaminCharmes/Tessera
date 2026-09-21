---
id: ticket-113
title: "Le dossier d'un ticket et son champ status ne peuvent plus diverger"
type: test
status: done
pr_number: 128
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-21
---

# ticket-113 — Le dossier d'un ticket et son champ status ne peuvent plus diverger

## Objectif

Mesurer une règle qui ne reposait que sur la discipline.

## Contexte

La règle est posée depuis le début, dans le skill `new-ticket` :

> Changer de statut = déplacer le fichier **et** mettre à jour le champ
> `status`. Les deux, sinon l'UI et le fichier divergent.

Rien ne la vérifiait. Sur une seule session de douze tickets, elle a été
enfreinte **trois fois** — 110, 111 et 112 sont restés en `in-progress` alors
que leur PR était ouverte, puis mergée. À chaque fois le même schéma : le code
écrit, les tests verts, la PR ouverte, la tâche paraît finie, et le
déplacement passe à la trappe.

C'est exactement le raisonnement d'ADR-034, appliqué à une autre règle : un
budget que rien ne mesure est un souhait, et une règle non plus. Le flux git
est testé, la longueur des ADR est testée, les chemins de machine sont
testés — le statut des tickets ne l'était pas.

## Solution proposée

Un test dans `test_consignes_coherentes.py` qui parcourt les dossiers de
`tickets/` et compare le nom de chaque dossier au champ `status` de chaque
ticket qu'il contient. Toute divergence nomme le fichier, le dossier et le
statut déclaré.

## Critères d'acceptation

- [x] Le test échoue si un ticket est rangé dans un dossier qui ne correspond
      pas à son champ `status`
- [x] Le message d'échec nomme le fichier, son dossier et son statut déclaré
- [x] Le test a été **vu échouer** sur un ticket témoin avant d'être gardé
- [x] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

Ne vérifie pas qu'un ticket dont la PR est ouverte soit en `in-review` : cela
demanderait d'interroger GitHub depuis la suite de tests, qui doit tourner
hors ligne. Le test attrape l'incohérence **interne**, pas le retard sur la
réalité de la PR.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un statut valide mais sans dossier correspondant — `cancelled` sans dossier
`cancelled/` — ne serait pas détecté, le test partant des dossiers existants.
C'est acceptable : le défaut visé est un fichier rangé au mauvais endroit, pas
un statut orphelin.
