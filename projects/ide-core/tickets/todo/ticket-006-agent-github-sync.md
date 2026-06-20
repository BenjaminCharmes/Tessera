---
id: ticket-006
title: "Agent github-sync — pont GitHub Issues ↔ tickets Markdown"
type: feat
status: todo
priority: medium
agent: codeur
depends_on:
  - ticket-003
created: 2026-06
---

# ticket-006 — Agent github-sync

## Contexte

L'architecture hybride de vibe-ide (décrite dans `docs/ticket-strategy.md`) prévoit
que les agents ne lisent jamais GitHub directement : ils consomment des fichiers
Markdown dans `tickets/todo/`.

Ce ticket implémente l'agent qui fait le pont entre les deux canaux.

## Tâche

Créer un agent `github-sync` qui :

1. **Poll les GitHub Issues** du dépôt configuré labelisées `agent-ready`
2. **Génère automatiquement** le fichier Markdown correspondant dans `tickets/todo/`
3. **Retire le label `agent-ready`** et ajoute `synced-to-agent` sur l'issue GitHub
4. **Évite les doublons** : ne crée pas de ticket si `github_issue_url` existe déjà

## Arborescence cible

```
backend/src/vibe_ide/
  agents/
    __init__.py
    github_sync.py     ← logique de l'agent
  services/
    github_service.py  ← client GitHub API (httpx, pas PyGitHub)
```

## Mapping GitHub Issue → Markdown

| Champ GitHub Issue        | Frontmatter Markdown        |
|---------------------------|-----------------------------|
| `title`                   | `title`                     |
| `body`                    | corps Markdown              |
| labels (feat/fix/chore…)  | `type`                      |
| `html_url`                | `github_issue_url`          |
| —                         | `status: todo`              |
| —                         | `agent: orchestrateur`      |
| —                         | `priority: medium` (défaut) |
| `number` + repo           | `id: ticket-NNN`            |

## Critères d'acceptation

- [ ] `POST /api/v1/agents/run` avec `role: github-sync` déclenche la synchro
- [ ] Les issues labelisées `agent-ready` génèrent un fichier dans `tickets/todo/`
- [ ] Le champ `github_issue_url` est renseigné dans le frontmatter
- [ ] Les doublons sont ignorés (idempotent)
- [ ] Tests avec mock GitHub API (httpx respx)
- [ ] `GITHUB_TOKEN` et `GITHUB_REPO` lus depuis les settings (pydantic-settings)

## Notes

- Utiliser `httpx` async (déjà dans les dépendances) plutôt que `PyGitHub`
- Pas de webhook pour la v0 — le poll suffit
- Le numéro d'issue GitHub sert de base pour l'`id` du ticket (`ticket-042` pour l'issue #42)
- Voir `docs/ticket-strategy.md` pour la vue d'ensemble de l'architecture
