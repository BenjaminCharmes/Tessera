---
id: ticket-053
title: "Couvrir la couche routers, là où naissent les bugs vécus"
type: test
status: done
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

- [x] Chaque router atteint **au moins 80 %** de couverture
- [x] La couverture backend globale ne descend pas sous 86 %
- [x] Chaque endpoint a un test du cas nominal et un test d'erreur
- [x] Les trois pannes du 2026-09-15 ont chacune un test de non-régression
      **au niveau du router**, pas seulement du service
- [x] Le seuil `fail_under` de pytest-cov est relevé à 85
- [x] `uv run pytest -q` et `uv run mypy src/` verts

## Dépendances

Aucune.

## Estimation

**2j**.

## Risques

- **Faible** — aucun code de production n'est censé changer. Si un test révèle
  un défaut, il devient un correctif à part entière, documenté comme tel.

## Résultat

| Module | Avant | Après |
|---|---|---|
| `routers/agents.py` | 39 % | **82 %** |
| `routers/chat.py` | 40 % | **88 %** |
| `routers/tickets.py` | 41 % | **93 %** |
| `routers/projects.py` | 48 % | **83 %** |
| `routers/orchestrator.py` | 53 % | **86 %** |
| `routers/agent_admin.py` | 91 % | 91 % |
| **Total backend** | 86 % | **93,5 %** |

611 → 674 tests. Seuil `fail_under` relevé de 70 à 85.

## Défaut trouvé par les tests

Un paramètre `status` invalide sur `GET /projects/{id}/tickets` levait un
`ValueError` non capturé : une faute de frappe dans l'URL produisait un 500
opaque. `_parse_status_filter` renvoie désormais un 422 qui énumère les valeurs
acceptées — même exigence qu'en ticket-051.

## Réserve assumée

Un `PytestUnhandledThreadExceptionWarning` subsiste sur la suite complète sous
Windows : course entre le thread interne d'aiosqlite et le portail de
`TestClient`, qui ouvre une connexion via le cycle de vie de l'application sans
toujours joindre son thread avant la fermeture de la boucle. Le fichier seul ne
le produit pas, la CI Linux non plus. Filtré avec sa justification dans
`pyproject.toml` : le harnais est en cause, aucun chemin de production.
