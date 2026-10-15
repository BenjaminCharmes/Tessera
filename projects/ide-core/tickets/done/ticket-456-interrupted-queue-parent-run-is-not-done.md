---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 0.5
id: ticket-456
pr_number: null
priority: high
status: done
title: An interrupted queue's parent run reports the interruption instead of done
type: fix
---

# ticket-456 — Le run parent d'une file interrompue ne se dit pas réussi

## Objectif

Une file arrêtée avant sa fin (« file interrompue : … ») apparaît comme
telle dans l'API des runs et dans l'interface.

## Contexte

make-your-call, 15/10 : la file 1ac647e9 s'arrête sur « file interrompue :
ticket-001 non mergé », la file c74dce05 sur la CI rouge du 007. Pourtant
`GET /api/v1/projects/make-your-call/runs` rend, pour ces runs parents,
`approved=True`, `final_status=done`, `arret=None`. Qui suit l'API croit la
file terminée et réussie. Le ticket-444 a distingué approuvés et bloqués
dans le statut d'une file, pas l'interruption.

La boucle de file est dans `backend/src/tessera/services/orchestrator.py`
(les `break` qui suivent « file interrompue »).

## Solution proposée

Quand la boucle sort par une interruption, le run parent garde la raison :
`arret` renseigné avec la ligne d'interruption, `approved=False`, et un
statut final qui ne vaut pas `done`.

## Critères d'acceptation

- [ ] Un test vérifie qu'une file interrompue sur un ticket non mergé
      enregistre un run parent avec `approved=False` et un `arret` qui
      contient « interrompue »
- [ ] Un test vérifie que le statut final de ce run parent n'est pas `done`
- [ ] Un test vérifie qu'une file menée à son terme garde `approved=True`