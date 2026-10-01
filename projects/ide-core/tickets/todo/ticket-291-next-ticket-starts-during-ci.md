---
id: ticket-291
title: "Design: a queue starts its next ticket while the previous one waits for CI"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: ["ticket-288"]
estimated_days: 1
created: 2026-10-01
---

# ticket-291 — La file démarre le ticket suivant pendant la CI du précédent

## Objectif

Décider, dans un ADR, comment une file cesse d'attendre la CI d'un ticket
avant de démarrer le suivant, et ce qu'elle fait quand cette CI est rouge.
Puis découper l'implémentation en tickets.

## Contexte

`run_pipeline` (`services/orchestrator.py:132-175`) documente, livre, puis
rend la main à `run_queue`. Or la livraison attend la CI
(`LivraisonService._attendre_la_ci`, jusqu'à 15 min) : pendant 2 min 30 à
4 min par ticket, l'arbre et les agents ne font rien. Sur une file de sept
tickets, une demi-heure se passe à attendre.

Ce qui change la donne : depuis le ticket-285, un run forke depuis
`origin/<base_branch>` à jour, et la livraison rebase sur cette même base
synchronisée. Le ticket N+1 peut donc partir **sans** le code du ticket N,
dont la PR n'est pas encore mergée.

## Proposition de départ (à éprouver, pas à recopier)

- La livraison se scinde : rebase, push et PR restent dans le run ; l'attente
  de CI et le merge passent dans une tâche de fond qui n'occupe pas l'arbre.
  Ils n'agissent que sur GitHub. Le `RunLock` (ADR-038) est libéré dès
  l'ouverture de la PR.
- Le ticket N+1 démarre aussitôt, **sauf** s'il déclare N dans `depends_on` :
  il attend alors le merge de N, comme aujourd'hui.
- CI de N verte : merge, la file continue normalement.
- CI de N rouge : N est remis en tête de file, avec la sortie de la CI comme
  retour au codeur, et relancé sur sa branche (reprise du ticket-220) dès la
  fin du run de N+1. N+1 n'a pas à être mis en pause : il ne contient pas le
  code de N. Au deuxième rouge, N passe en `blocked`, et les tickets qui en
  dépendent avec lui.
- Au plus une livraison en attente de CI à la fois. Un N+1 approuvé pendant
  que N attend encore attend lui-même avant d'ouvrir sa PR.
- Un N+1 qui touche les mêmes fichiers que N entre en conflit au rebase. Il
  passe par ADR-033 : la PR s'ouvre et **ne se merge pas seule**.

## Questions que l'ADR doit trancher

- Ce que voit l'UI : un run clos (`run_closed`, ADR-041) dont la livraison
  continue. Quel événement, sur quel run, et où s'affiche-t-il ?
- Ce que devient la livraison de fond si le backend s'arrête : reprise au
  démarrage, ou PR laissée ouverte et signalée.
- ADR-030 dit que la livraison ne fait jamais échouer le run. Un rouge qui
  relance N le contredit-il, ou bien est-ce un nouveau run ?
- Les conflits fréquents sur `memory/decisions.md` et `pipeline-log.md`
  rendent-ils le gain illusoire ? Les chiffres du ticket-288 le diront.

## Critères d'acceptation

- [ ] `memory/decisions.md` contient un ADR qui décrit le découpage de la
      livraison, la règle de démarrage du ticket suivant et le repli sur une
      CI rouge
- [ ] L'ADR répond à chacune des quatre questions ci-dessus
- [ ] L'ADR nomme les ADR qu'il amende parmi 018, 030, 038 et 041
- [ ] `tickets/todo/` contient les tickets d'implémentation, chacun limité à
      une couche (backend ou frontend) et à six critères au plus

## Dépendances

ticket-288 : la durée réelle de l'attente de CI et de la documentation dit
combien ce chantier rapporte.

## Estimation

1 jour pour l'ADR et le découpage.

## Risques

Ce ticket touche aux garanties d'ADR-018 (arbre propre, base qui n'avance que
sur approbation) et d'ADR-038 (un run par projet). Une erreur ici ne casse
pas un test, elle mélange l'historique de deux tickets.
