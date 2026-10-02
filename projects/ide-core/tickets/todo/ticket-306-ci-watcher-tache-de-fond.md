---
id: ticket-306
title: "CIWatcher waits for CI and merges in the background, one delivery per project"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-305"]
estimated_days: 1
plan: true
created: 2026-10-02
---

# ticket-306 — CIWatcher attend la CI et merge en tâche de fond

## Objectif

Créer `CIWatcher`, qui tient en mémoire du process les attentes de CI et les
merges, avec au plus une livraison en attente par projet.

## Contexte

ADR-051. Une fois la PR ouverte (ticket-305), le run libère son verrou, et
`CIWatcher` prend le relais sans tenir l'arbre.

**Décision du 2026-10-02, qui amende ADR-051 :** une CI rouge met le ticket
en `blocked`, avec la PR laissée ouverte et un `arret` qui nomme le job en
échec. Elle ne relance pas de run automatiquement. Depuis le ticket-304, le
testeur lance les mêmes contrôles que la CI : une CI rouge devient donc rare,
et elle mérite un regard humain plutôt qu'un nouveau run complet.

## Contrat

```python
class CIWatcher:
    async def surveiller(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        livraison_phase_2: Callable[[int], Awaitable[Livraison]],
        on_event: EventCallback,
    ) -> None: ...

    def en_attente(self, project_id: str) -> tuple[str, ...]:
        """Ticket ids whose PR is open and waiting for CI or merge."""
```

## Critères d'acceptation

- [ ] Un test vérifie qu'une seconde livraison du même projet attend la fin
      de la première, et que deux projets différents ne s'attendent pas
- [ ] Un test vérifie qu'une CI verte mène au merge et émet
      `ci_merge_done` avec `{project_id, ticket_id, pr_number, merged: true,
      arret: null}`
- [ ] Un test vérifie qu'une CI rouge passe le ticket en `blocked` et émet
      `ci_merge_done` avec `merged: false` et un `arret` qui contient le
      numéro de la PR
- [ ] Un test vérifie que `en_attente(project_id)` liste le ticket pendant
      l'attente, puis plus après `ci_merge_done`
- [ ] Un test vérifie qu'à l'arrêt, les tâches en cours sont annulées sans
      lever d'exception

## Dépendances

ticket-305 (`livrer_phase_2`).

## Périmètre

`backend/src/tessera/services/ci_watcher.py` (nouveau) et
`services/pipeline_events.py` (`CI_MERGE_DONE`). ADR-051 est déjà amendé.
