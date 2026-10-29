---
id: ticket-679
title: "Response models for the services routes"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-679 — Modèles de réponse pour `routers/services.py`

## Objectif
Les trois routes de lancement et de liste des services déclarent leur réponse.

## Contexte
`routers/services.py` : `start` rend `{"services": …}` (ligne 143), `stop`
`{"arretes": n}` (149), `lister` `list[dict[str, object]]` (153, via
`Service.en_dict()`), sans `response_model` (`docs/audit/doublons.md` §1.5). Le
front les type à la main (`lib/api.ts:193-196`, `ServiceActif`).

## Critères d'acceptation
- [ ] Un modèle Pydantic décrit la réponse de `start`, `stop` et `lister` ; chaque route le déclare en `response_model`
- [ ] `Service.en_dict()` est remplacé par le modèle ou en dérive ; un test confronte les clefs du modèle à celles de `ServiceActif` dans `types/api.ts`
- [ ] Le JSON rendu est identique octet pour octet à celui d'avant sur un cas de test
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne change pas le comportement de lancement ni d'arrêt des services (ADR-042)
- Ne touche pas `routers/services.py` hors de ses annotations et de ses retours
