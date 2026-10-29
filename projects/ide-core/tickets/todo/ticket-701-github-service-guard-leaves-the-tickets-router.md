---
id: ticket-701
title: "The GitHub service guard leaves the tickets router"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-701 — Le garde `_require_github_service` hors de `routers/tickets.py`

## Objectif
Un routeur n'importe plus le nom privé d'un autre routeur : le garde partagé
vit dans le module de dépendances que les routeurs importent déjà.

## Contexte
`routers/ticket_proposals.py:11` importe `_require_github_service` depuis
`routers/tickets.py` (défini en 186, utilisé en 210, 249 et 309). C'est un
import de nom privé entre routeurs, que le test du ticket-670 refusera
(`docs/audit/refactos.md` §2.1). `routers/dependencies.py` existe déjà et porte
`require_valid_project_id` pour huit routeurs.

## Critères d'acceptation
- [ ] `grep -rn "routers.tickets import" backend/src` ne rend aucune ligne
- [ ] `grep -rn "def _require_github_service\|def require_github_service" backend/src` ne rend qu'une définition, dans `routers/dependencies.py`
- [ ] Le garde garde son comportement : mêmes codes HTTP et mêmes messages quand le projet n'a pas de `github_remote` ; les tests existants de `tickets` et de `ticket_proposals` passent sans changement de leurs attendus (seule une cible de `patch` peut changer de nom)
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne découpe pas `routers/tickets.py` (voir `docs/audit/refactos.md` §5)
- Ne touche pas à `chat.py:357` (ticket-687)
