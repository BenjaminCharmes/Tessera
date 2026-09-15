---
id: ticket-053
title: "Couvrir la couche routers, là où naissent les bugs vécus"
type: test
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-15
---

# ticket-053 — Couverture de la couche routers

## Objectif

Amener les routers au niveau de couverture des services, parce que c'est la
couche où les défauts atteignent réellement l'utilisateur.

## Contexte

La couverture backend est à 86 % — mais très inégalement répartie :

| Module | Couverture |
|---|---|
| `routers/agents.py` | 39 % |
| `routers/chat.py` | 40 % |
| `routers/tickets.py` | 41 % |
| `routers/projects.py` | 48 % |
| `routers/orchestrator.py` | 53 % |
| Services | 86 – 100 % |

Ce n'est pas une statistique abstraite. **Les trois pannes rencontrées en
utilisant l'application le 2026-09-15 sont toutes dans cette couche ou sa
configuration** :

- `409` à l'import d'un projet — chemin entre guillemets résolu depuis le cwd
  du backend (`routers/projects.py` → `project_importer`)
- `500` sur « Planifier une évolution » — clef API parasite et prompts
  introuvables (`routers/projects.py` → `planner`)
- `500` opaques sur toute action d'agent — aucun message exploitable

Les services étaient testés ; l'assemblage ne l'était pas. Un test de service
ne voit ni le parsing de la requête, ni le code HTTP, ni le `detail` renvoyé.

## Solution proposée

Un fichier de tests par router, via `TestClient`, couvrant pour chaque endpoint :

1. **Le cas nominal** — code HTTP et forme de la réponse
2. **Les erreurs métier** — 404 sur ressource absente, 409 sur conflit, et le
   **contenu** du `detail` (un message inexploitable est un bug, cf. ticket-051)
3. **La validation d'entrée** — payload incomplet, type invalide, chemin relatif
4. **Les chemins WebSocket** — trames émises dans l'ordre attendu

## Hors périmètre

- Les appels LLM réels : les providers sont doublés
- La couverture frontend, déjà à son seuil

## Critères d'acceptation

- [ ] Chaque router atteint **au moins 80 %** de couverture
- [ ] La couverture backend globale ne descend pas sous 86 %
- [ ] Chaque endpoint a un test du cas nominal et un test d'erreur
- [ ] Les trois pannes du 2026-09-15 ont chacune un test de non-régression
      **au niveau du router**, pas seulement du service
- [ ] Le seuil `fail_under` de pytest-cov est relevé à 85
- [ ] `uv run pytest -q` et `uv run mypy src/` verts

## Dépendances

Aucune.

## Estimation

**2j**.

## Risques

- **Faible** — aucun code de production n'est censé changer. Si un test révèle
  un défaut, il devient un correctif à part entière, documenté comme tel.
