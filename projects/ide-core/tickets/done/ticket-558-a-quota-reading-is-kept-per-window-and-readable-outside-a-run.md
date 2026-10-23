---
agent: codeur
created: 2026-10-23
depends_on: []
estimated_days: 1
id: ticket-558
pr_number: 632
priority: medium
status: done
title: A quota reading is kept per window and can be read outside a run
type: feat
---

# ticket-558 — Un relevé de quota par fenêtre, lisible hors d'un run

## Objectif
Donner au tableau du jour (ticket-565) le quota de la session (5 h) et celui
de la semaine, chacun avec son heure de reprise, sans qu'un run soit en cours.

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md`, ligne
« quota ». `QuotaTracker` (`services/quota_tracker.py`) naît avec chaque
`AgentSdkProvider`, garde un seul relevé toutes fenêtres confondues et ne se
diffuse (`quota_updated`) que lorsqu'une file s'arrête sur quota bas. Le SDK
distingue pourtant `five_hour`, `seven_day`, `seven_day_opus`,
`seven_day_sonnet` et `overage` (`RateLimitInfo.rate_limit_type`), et n'émet un
relevé que sur changement d'état : « pas de relevé » est le cas nominal.

## Solution proposée
Un registre au niveau du processus (comme `RUN_REGISTRY`, ADR-008 : rien dans
l'orchestrateur) qui garde le dernier relevé de chaque fenêtre, avec l'instant
où il a été lu. `QuotaTracker.observe` y inscrit chaque relevé normalisé ; son
comportement par run ne change pas. Un relevé dont `resets_at` est passé n'est
plus rendu : la fenêtre a recommencé, on ne sait plus rien. Un nouvel endpoint
`GET /usage/quota` rend `{ "windows": { "<fenêtre>": { status, utilization,
resets_at, observed_at } } }`, vide quand rien n'est connu.

## Critères d'acceptation
- [ ] Deux relevés de fenêtres différentes (`five_hour`, `seven_day`) coexistent dans le registre, et un test le vérifie
- [ ] Un second relevé de la même fenêtre remplace le premier, et un test le vérifie
- [ ] Un relevé dont `resets_at` est dans le passé n'est pas rendu par le registre, et un test le vérifie avec une horloge simulée
- [ ] Un relevé sans fenêtre est gardé sous la clé `unknown` et n'est jamais rendu comme `five_hour` ni `seven_day`, et un test le vérifie
- [ ] `GET /usage/quota` rend `{"windows": {}}` quand aucun relevé n'existe, et le relevé de chaque fenêtre quand il y en a, et un test le vérifie
- [ ] `snapshot`, `is_low`, `is_exhausted` et `as_event_data` de `QuotaTracker` se comportent comme avant : les tests existants passent sans modification
- [ ] Le diff ne modifie aucun fichier de `frontend/`

## Ce que ça ne fait pas
- Ne garde rien après un redémarrage du backend : un relevé se reconstitue au premier événement du SDK.
- Ne change pas l'arrêt du mode autonome entre deux tickets (`is_low`, ADR-020).
- N'affiche rien : l'écran est le ticket-565.