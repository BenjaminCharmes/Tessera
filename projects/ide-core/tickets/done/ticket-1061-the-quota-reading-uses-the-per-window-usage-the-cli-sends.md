---
agent: codeur
created: 2026-11-27
depends_on: []
estimated_days: 1
id: ticket-1061
pr_number: null
priority: medium
status: done
title: The quota reading uses the per-window usage the CLI sends
type: fix
---

# ticket-1061 — Le relevé de quota lit l'usage par fenêtre que le CLI envoie

## Objectif

`GET /api/v1/usage/quota` rend la session (5 h) et la semaine dès qu'un appel
d'agent a eu lieu, au lieu de `{"windows":{}}` en permanence.

## Contexte

Le 27/11, après des heures de runs sur un backend démarré à 09:01, la route
renvoyait `{"windows":{}}`. Ce n'est pas l'absence d'événement : le CLI embarqué
envoie bien un `RateLimitEvent`, mais son `rate_limit_info.utilization` de
premier niveau est `None` quand le statut est `allowed`. L'usage de chaque
fenêtre est dans `rate_limit_info.raw["unifiedWindows"]`, sous les clés
`five_hour` et `seven_day`, chacune avec `utilization`, `resetsAt` (secondes
epoch) et `status`. Relevé réel du 27/11 : `utilization=None` en tête, et
`unifiedWindows = {five_hour: {utilization: 0.15, ...}, seven_day: {utilization: 0.56, ...}}`.

`snapshot_from_rate_limit` (`backend/src/tessera/services/usage/quota_tracker.py`)
rend `None` dès que `utilization` de premier niveau n'est pas un nombre, donc
`QuotaTracker.observe` n'inscrit rien dans `QUOTA_REGISTRY`
(`backend/src/tessera/services/usage/quota_registry.py`), et la route comme le
garde d'`is_low` restent aveugles. Seul un événement `allowed_warning` portant
l'usage en tête passait.

## Solution proposée

Dans `quota_tracker.py` :
- une fonction `snapshots_from_rate_limit(info)` rend la liste des
  `QuotaSnapshot` lisibles : un par entrée de `raw["unifiedWindows"]` qui porte
  un `utilization` numérique (fenêtre = la clé, `resets_at` depuis `resetsAt`,
  statut depuis `status`, repli sur `allowed`), plus le relevé de premier niveau
  de `snapshot_from_rate_limit` s'il existe et que sa fenêtre n'est pas déjà
  couverte. Un `raw` absent ou mal formé donne une liste vide, sans exception ;
- `QuotaTracker.observe` inscrit chaque relevé dans `QUOTA_REGISTRY`, et garde
  comme relevé du run celui de plus forte utilisation (c'est la fenêtre qui
  limite), de sorte que `is_low` et `is_exhausted` voient aussi la semaine ;
- `snapshot_from_rate_limit` garde son comportement : `None` sans `utilization`
  de premier niveau.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_quota_tracker.py` donne à `observe` un
      objet dont `utilization` vaut `None` et dont `raw` porte `unifiedWindows`
      avec `five_hour` à 0.15 et `seven_day` à 0.56 : `QUOTA_REGISTRY.readings()`
      contient les deux fenêtres, avec leurs `resets_at` en UTC.
- [ ] Un test montre que `QuotaTracker.snapshot` est alors la fenêtre à 0.56, et
      qu'`is_low` passe à vrai quand la semaine atteint 0.92.
- [ ] Un test montre qu'un `raw` absent, vide ou sans `unifiedWindows` laisse
      `observe` rendre `None` sans exception, et le registre vide.
- [ ] Un test montre qu'une entrée de `unifiedWindows` sans `utilization`
      numérique est ignorée, les autres restant lues.
- [ ] Un test de la route `GET /usage/quota` (dans le fichier de tests de la
      route existant, ou à côté) rend les deux fenêtres après un `observe` de
      ce relevé réel.
- [ ] Les tests existants de `test_quota_tracker.py` sur `snapshot_from_rate_limit`
      passent inchangés.
- [ ] Aucun fichier de `frontend/` n'est modifié.

## Ce que ça ne fait pas

- Ne persiste rien : le registre reste en mémoire, un redémarrage le vide
  jusqu'au premier appel d'agent.
- Ne lit pas la fenêtre `overage` ni les fenêtres par modèle.
- Ne change pas le seuil d'`is_low` (0.90).
- Le backend doit être redémarré pour prendre le correctif ; c'est à la session
  ide-core de le faire, pas au run.

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

`is_low` voit désormais la semaine : le mode autonome peut s'arrêter à 0.90
d'usage hebdomadaire, ce qu'ADR-020 prévoyait sans que le CLI le permette.