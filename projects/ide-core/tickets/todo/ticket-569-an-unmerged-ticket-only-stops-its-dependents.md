---
id: ticket-569
title: "A ticket that does not merge stops only the queue tickets that depend on it"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-23
plan: true
---

# ticket-569 — Un ticket non mergé n'arrête que ceux qui en dépendent

## Objectif
Qu'une CI rouge sur un ticket n'arrête pas une file de dix tickets, quand la
plupart n'en dépendent pas.

## Contexte
`_attendre_si_dependant` (`services/orchestrator.py`) attend le merge d'un
ticket dès qu'**un** ticket restant en dépend ; si le merge échoue, la file
entière s'interrompt (`file interrompue : … non mergé`). Le 23/10, la CI
rouge du ticket-544 a arrêté onze tickets parce que le seul ticket-546 en
dépendait ; les dix autres auraient pu tourner pendant la correction.

## Solution proposée
Quand un ticket n'est pas mergé : retirer de la file les tickets qui en
dépendent, directement ou par transitivité (`depends_on`), les journaliser
(« ticket-546 sauté : dépend de ticket-544, non mergé ») et continuer avec
les autres. La file ne s'arrête que s'il ne reste plus rien. Le ticket non
mergé reste `blocked`, PR ouverte, comme aujourd'hui (ADR-051). Une ADR au
prochain numéro libre de `memory/decisions.md` complète l'ADR-051.

## Critères d'acceptation
- [ ] Un test, avec des doubles, montre qu'un ticket non mergé fait sauter le ticket qui en dépend et laisse la file continuer avec un ticket indépendant
- [ ] Un test montre qu'une dépendance transitive (C dépend de B, qui dépend de A) est aussi sautée quand A n'est pas mergé
- [ ] Un test montre qu'un ticket sauté écrit une ligne dans `memory/pipeline-log.md` qui nomme sa dépendance
- [ ] Un test montre que la file s'arrête quand tous les tickets restants dépendent du ticket non mergé
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit la règle et renvoie à l'ADR-051
