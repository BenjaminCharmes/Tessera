---
id: ticket-453
title: "A rebase conflict at delivery is handed to the conflict resolver, or says why not"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
plan: true
created: 2026-10-15
---

# ticket-453 — Un conflit de rebase passe au résolveur, ou dit pourquoi pas

## Objectif

Un conflit au rebase de livraison est soumis à `resolveur-conflit`
(ADR-033) ; quand il ne l'est pas, la ligne d'arrêt dit pourquoi.

## Contexte

make-your-call, 15/10, run 968ea9a0 : « 10:43:44 [ticket-005] livraison :
arrêt — Conflit avec main sur : prisma/schema.prisma. La branche est restée
intacte, à toi de trancher. » Aucune ligne de tentative du résolveur,
`pr_number` null, branche jamais poussée. Trois tickets (002, 003, 005)
touchaient ce fichier. Le rôle est intégré (`BUILTIN_ROLES` dans
`backend/src/tessera/services/agent_registry.py`) et câblé dans
`backend/src/tessera/routers/orchestrator.py` quand un runner existe ;
`agents.json` de make-your-call ne le déclare pas. Le plan doit établir
pourquoi le résolveur n'a pas été appelé (rôle non déclaré, type de fichier
écarté, condition de `backend/src/tessera/services/resolveur_conflit.py`).

## Solution proposée

- Corriger la cause si le résolveur aurait dû tenter.
- Sinon, la ligne d'arrêt nomme la raison (« résolveur non tenté :
  <raison> »).

## Critères d'acceptation

- [ ] Un test reproduit un conflit de rebase sur un fichier de code d'un
      projet dont `agents.json` ne déclare pas `resolveur-conflit`, et
      vérifie que le résolveur est appelé, ou que l'arrêt contient
      « résolveur non tenté »
- [ ] La cause observée sur make-your-call est décrite dans la PR
