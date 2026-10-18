---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.25
id: ticket-486
pr_number: 525
priority: medium
status: done
title: The CI watcher blocked-ticket test waits for its event instead of sleeping
  50 ms
type: test
---

# ticket-486 — Un test du CIWatcher attend son événement

## Objectif

`test_exception_passe_le_ticket_en_blocked` ne dépend plus de la vitesse de
la machine.

## Contexte

16/10 : la CI de la PR #497 (ticket-476) a échoué sur ce test seul,
`assert len(status_events) == 1` avec 0 événement ; une relance est passée.
Le même test avait déjà échoué une fois en local. Dans
`backend/tests/test_ci_watcher.py`, il lance la surveillance en tâche de fond
puis attend `asyncio.sleep(0.05)` avant de lire les événements : sur une
machine chargée, la tâche n'a pas encore émis.

## Solution proposée

Attendre la fin de la tâche de surveillance (par exemple `await
watcher.attendre_merge("proj", "ticket-001")`, ou un `asyncio.Event` posé par
le collecteur, avec un délai maximal de quelques secondes) au lieu d'un
`sleep` fixe. Chercher dans `backend/tests/test_ci_watcher.py` les autres
`asyncio.sleep` fixes qui précèdent une assertion et les traiter de même.

## Critères d'acceptation

- [ ] `test_exception_passe_le_ticket_en_blocked` n'utilise plus
      `asyncio.sleep` avant ses assertions
- [ ] Aucun test de `backend/tests/test_ci_watcher.py` n'attend un délai
      fixe avant une assertion sur des événements
- [ ] Les tests du fichier passent 20 fois de suite (`pytest --count=20` ou
      une boucle), dit la PR
## Vérification des 20 passages

`tests/test_ci_watcher.py` lancé 20 fois de suite, une boucle de
`uv run python -m pytest tests/test_ci_watcher.py -q -p no:cacheprovider`
depuis `backend/` : 20 passages, chacun `32 passed`, aucun échec. Les `sleep`
fixes avant assertion sont remplacés par `_attendre_fin`, qui attend la fin
réelle de la surveillance (plafond de 5 s contre un blocage).