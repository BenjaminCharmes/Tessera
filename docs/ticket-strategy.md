# Stratégie de gestion des tickets

## Principe

Tessera utilise une architecture **hybride** qui sépare les canaux humain et agent
tout en maintenant une synchronisation optionnelle entre eux.

---

## Sources de vérité

### GitHub Issues — canal humain

- Tickets créés par des humains (bugs remontés, feature requests, discussions)
- Visibles publiquement et commentables
- Labellisés `agent-ready` quand ils sont prêts à être pris en charge par un agent
- **Ne sont jamais lus directement par les agents**

### Fichiers Markdown (`tickets/`) — canal agent

- Source de vérité pour l'orchestrateur et tous les agents
- Format : frontmatter YAML + corps Markdown
- Organisation par statut : `todo/`, `in-progress/`, `in-review/`, `done/`, `blocked/`, `archive/`
- Lisibles sans l'IDE (plain text dans le repo)
- Champ optionnel `github_issue_url` pour tracer l'origine GitHub

---

## Workflow

```
GitHub Issue (humain)
        │
        │  labelisé "agent-ready"
        ▼
  POST /api/v1/agents/run { role: "github-sync", project_id }
        │  (agent github-sync — ticket-006 ✅)
        │  génère automatiquement
        ▼
tickets/todo/ticket-NNN.md  ←── source de vérité agent
        │
        │  POST /api/v1/orchestrator/run { project_id, ticket_id }
        ▼
  in-progress → in-review → done (ou blocked après 3 tours)
        │
        ▼
     archive/ (après 30 jours en done)
```

---

## Règles

1. **Les agents ne lisent jamais GitHub directement** — ils consomment uniquement
   les fichiers Markdown.
2. **Un ticket Markdown peut exister sans issue GitHub** — les tickets internes
   (chores, design) n'ont pas forcément de contrepartie publique.
3. **Le champ `github_issue_url` est informatif**, pas structurant — il permet
   de retrouver le contexte humain sans en dépendre.
4. **La synchronisation est bidirectionnelle** (depuis `ticket-031`) : GitHub → Markdown
   (`pull`) et Markdown → GitHub (`push`), avec un mapping persistant par projet pour
   rester idempotente et éviter les collisions d'ID.

---

## Agent github-sync ✅

Sync initiale (`pull` uniquement) implémentée dans `ticket-006`, étendue en
bidirectionnel (`pull` / `push` / `both`) dans `ticket-031`. Feature optionnelle,
activée par projet via `agents.json` :

```json
{
  "github_sync": {
    "enabled": true,
    "direction": "both",
    "label_map": { "feat": "enhancement", "fix": "bug" }
  }
}
```

Déclenché via :
```bash
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/github/sync \
  -H "Content-Type: application/json" \
  -d '{"direction": "both"}'
```

Réponse : `{ "pulled": 3, "pushed": 1, "skipped": 2 }`

Configuration requise dans `.env` :
```
GITHUB_TOKEN=ghp_...
GITHUB_REPO=owner/repo
```

### Mode `pull` (issues → tickets)

| GitHub Issue       | Frontmatter Markdown     |
|--------------------|--------------------------|
| title              | title                    |
| body               | corps Markdown           |
| labels (feat/fix…) | type                     |
| html_url           | github_issue_url         |
| number             | id (assigné sans collision, jamais `issue_number` directement) |
| —                  | status: todo             |
| —                  | agent: orchestrateur     |
| —                  | priority: medium         |

Après sync :
- Label `agent-ready` retiré de l'issue
- Label `synced-to-agent` ajouté sur l'issue
- Idempotent : une issue déjà syncée (même `github_issue_url`) est ignorée

### Mode `push` (tickets → issues)

- Un ticket `done` sans issue associée → crée une issue **fermée** sur GitHub
- Un ticket déjà mappé (`memory/github-sync-map.json`) → met à jour l'issue existante
  plutôt que d'en recréer une

### Mapping & idempotence

Le mapping ticket ↔ issue est persisté dans `memory/github-sync-map.json` (par projet)
et chaque opération est tracée dans `memory/github-sync-log.md`. Deux syncs successives
ne créent jamais de doublons.
