---
agent: codeur
created: 2026-10-17
depends_on: []
estimated_days: 1
id: ticket-497
plan: true
pr_number: null
priority: medium
status: done
title: A resumed ticket whose branch already carries work runs the tests first, and
  goes straight to review when they pass
type: feat
---

# ticket-497 — Un ticket repris sur une branche déjà travaillée ne rejoue pas le codeur

## Objectif

Quand un run reprend un ticket dont la branche porte déjà du travail
(interruption, quota épuisé, redémarrage), le pipeline vérifie ce travail
avant de rappeler le codeur : des tests verts mènent directement à l'audit et
à la revue.

## Contexte

`GitWorkspaceService` sait déjà reprendre la branche existante d'un ticket et
la rejouer sur une base qui a avancé (tickets 208 et 329). Mais le pipeline
repart toujours du premier tour du codeur. Le 17/10, après l'épuisement du
quota la veille au soir, Kadoomi (ticket-014) et Devinoo (ticket-018) ont repris
sur des branches déjà vertes (435/435 tests pour le 018). Un tour de codeur
complet, le plus cher du pipeline, est rejoué pour redécouvrir un travail
fini.

## Solution proposée

1. À l'ouverture d'un ticket, une branche reprise qui porte des commits
   au-delà de son point de départ (`_fork_point`) est marquée « travail
   existant ».
2. Dans ce cas, et seulement si le testeur est actif sur le projet, le
   pipeline lance d'abord le testeur sur l'arbre tel quel :
   - tests verts → il saute le premier tour du codeur et enchaîne audit,
     revue, validateur, comme après un tour de codeur normal ;
   - tests rouges, panne d'environnement ou délai dépassé → il reprend le
     déroulé habituel, codeur en premier, avec le résultat de ces tests dans
     son prompt.
3. L'événement `run_resumed_from_existing_work` (ticket, nombre de commits
   repris, verdict des tests) est émis et écrit dans `pipeline-log.md`.
4. Un refus de la revue ou du validateur renvoie au codeur comme d'habitude :
   rien ne change au-delà du premier tour.

## Ce que ça ne fait pas

- Ne reprend pas au milieu d'une étape (pas de reprise de session d'agent).
- Ne saute rien sur un projet sans testeur : sans tests, rien ne prouve que le
  travail repris tient.
- Ne touche pas aux portes d'audit et de validation, qui jugent toujours.

## Critères d'acceptation

- [ ] Un test vérifie qu'une branche reprise avec des commits au-delà de son
      point de départ, tests verts, n'appelle pas le codeur avant la revue
- [ ] Un test vérifie que des tests rouges sur une branche reprise appellent
      le codeur avec le résultat de ces tests dans son prompt
- [ ] Un test vérifie qu'une branche neuve appelle le codeur en premier,
      comme avant
- [ ] Un test vérifie que, sur un projet sans testeur, une branche reprise
      appelle le codeur en premier
- [ ] Un test vérifie l'émission de `run_resumed_from_existing_work` avec le
      verdict des tests

## Risques

Un travail repris vert mais incomplet passe en revue sans nouveau tour de
codeur : c'est la revue et le validateur, qui lisent les critères en entier,
qui le renvoient alors au codeur, ce qu'ils font déjà pour un premier tour
incomplet.