---
id: ticket-687
title: "Run assembly leaves the orchestrator router"
type: refactor
status: todo
priority: medium
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-687 — L'assemblage d'un run quitte `routers/orchestrator.py`

## Objectif
Le routeur ne porte que ses modèles de requête et ses endpoints ; la
construction de l'orchestrateur (provider par rôle, contexte, livreur,
documenteur, surveillance) vit dans `services/`.

## Contexte
`routers/orchestrator.py` fait 1089 lignes dont ≈ 700 d'assemblage
(`_build_orchestrator` 169 lignes, `_livreur` 104, `_surveillance_pour`,
`_workflow_de_lecture`, `_documenteur`, 180-884). `routers/chat.py:357`
importe `_build_orchestrator` depuis ce routeur : un routeur qui en importe un
autre, par un nom privé. Le ticket-670 (sens des imports) échoue tant que
c'est le cas. `docs/audit/refactos.md` §2.1.

## Critères d'acceptation
- [ ] `grep -rn "routers.orchestrator import" backend/src` ne rend aucune ligne, et `grep -rn "def _build_orchestrator" backend/src/tessera/routers` non plus ; `routers/chat.py` appelle l'assemblage depuis `services/`
- [ ] Les imports de `tessera.routers.dependencies` et de `tessera.routers.services_running` (modules partagés, importés par huit routeurs) ne sont pas touchés
- [ ] L'assemblage reste une fonction qui construit un `Orchestrator` neuf à chaque appel, sans état conservé (ADR-008)
- [ ] L'entrée de `routers/orchestrator.py` dans `PLAFONDS` est baissée à 450 ou moins
- [ ] Les couples (méthode, chemin) de `app.openapi()["paths"]` sont identiques avant et après ; un test les fige
- [ ] Les tests qui patchent un nom déplacé sont mis à jour sans changement de leurs attendus ; la PR liste les cibles de `patch` modifiées
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne change aucun endpoint (ADR-041) ni la politique d'un run
- Ne traite pas l'import de `_require_github_service` par `ticket_proposals.py` (ticket-701)
- Ne dédouble pas `_livreur` / `surveillance_de_reprise` : ils bougent, ils ne se recopient pas
- N'implémente pas le test d'imports (ticket-670)
