---
agent: codeur
created: '2026-10-22'
depends_on: []
id: ticket-537
priority: medium
status: todo
title: Le validateur ignore une réponse du dialogue qui change le sens d un critère,
  et le run se bloque
type: feat
---

## Signalement

- Projet source : kadoomi
- Nature : idee
- Reçu le : 2026-10-22

## Description

Run d10b5e00 (kadoomi, ticket-088, 22/10). Au tour 1, le codeur pose une question (agent_question) : le critère 2 demande un 404, mais un 404 distinct ferait oracle et casserait le toast Annuler ; il propose A (404) ou B (état vide). La session du projet répond B. Le codeur implémente B ; reviewer APPROVED, audit PASS, tests verts. Mais le validateur ne voit que le texte du ticket et refuse le critère 2 trois tours de suite : run blocked, ticket fini à la main. Un interject demandant au codeur de reformuler le critère dans le fichier du ticket est arrivé trop tard. Gain attendu : un run qui suit une décision prise au dialogue ne se bloque pas sur un texte périmé.

## Contexte

Pistes : joindre au validateur les questions et réponses du dialogue du run ; ou laisser le codeur proposer un amendement de critère (visible dans le diff du ticket), à confirmer par l humain au dialogue.

## Critères d'acceptation

- [ ] À écrire au triage