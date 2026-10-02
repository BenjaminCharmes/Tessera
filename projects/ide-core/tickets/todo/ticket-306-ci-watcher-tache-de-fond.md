---
id: ticket-306
title: "CIWatcher : attente CI et merge en tâche de fond par projet"
type: feat
status: todo
priority: high
agent: codeur
---

# ticket-306 — CIWatcher : attente CI et merge en tâche de fond par projet

## Objectif

Créer `CIWatcher`, un singleton en mémoire du process qui gère les tâches
de fond d'attente CI + merge, à raison d'une tâche active par projet
(sémaphore). CI rouge : remet le ticket en `todo` et déclenche un nouveau run.
Au deuxième rouge consécutif : ticket en `blocked`.

## Contexte

ADR-051. Une fois la PR ouverte (ticket-305), le run libère son verrou.
`CIWatcher` prend le relais sans tenir l'arbre.

## Contrat

```python
class CIWatcher:
    async def surveiller(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        branch: str,
        livraison_phase_2: Callable[..., Awaitable[Livraison]],
        on_event: EventCallback,
    ) -> None: ...
```

## Critères d'acceptation

- [ ] Au plus une tâche de fond active par projet (sémaphore `asyncio.Semaphore(1)`)
- [ ] CI verte : `livraison_phase_2` mergée, `CI_MERGE_DONE` émis sur le canal projet
- [ ] CI rouge : ticket repassé `todo` (champ `description` = log CI), nouveau run
      déclenché ; au deuxième rouge consécutif sur le même ticket, `blocked`
- [ ] Arrêt propre du backend : les tâches en cours sont annulées proprement
      (les PRs restent ouvertes sur GitHub — état sûr)
- [ ] `CI_MERGE_DONE` porte `{project_id, ticket_id, pr_number, merged: bool, arret}`
- [ ] Tests unitaires : CI verte → merge, CI rouge × 1 → relance, CI rouge × 2 → blocked

## Dépendances

ticket-305 (`livrer_phase_2` disponible)

## Périmètre

`backend/src/tessera/services/ci_watcher.py` (nouveau fichier).
