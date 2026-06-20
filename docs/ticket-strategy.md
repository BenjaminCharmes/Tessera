# Stratégie de gestion des tickets

## Principe

vibe-ide utilise une architecture **hybride** qui sépare les canaux humain et agent
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
4. **La synchronisation est unidirectionnelle** pour la v0 : GitHub → Markdown.
   Le retour (mise à jour des issues depuis les tickets) est prévu en v1.

---

## Agent github-sync ✅

Implémenté dans `ticket-006`. Déclenché via :
```bash
curl -X POST http://localhost:8000/api/v1/agents/run \
  -H "Content-Type: application/json" \
  -d '{"project_id": "mon-projet", "role": "github-sync"}'
```

Configuration requise dans `.env` :
```
GITHUB_TOKEN=ghp_...
GITHUB_REPO=owner/repo
```

| GitHub Issue       | Frontmatter Markdown     |
|--------------------|--------------------------|
| title              | title                    |
| body               | corps Markdown           |
| labels (feat/fix…) | type                     |
| html_url           | github_issue_url         |
| number             | id (`ticket-{number:03d}`) |
| —                  | status: todo             |
| —                  | agent: orchestrateur     |
| —                  | priority: medium         |

Après sync :
- Label `agent-ready` retiré de l'issue
- Label `synced-to-agent` ajouté sur l'issue
- Idempotent : une issue déjà syncée (même `github_issue_url`) est ignorée
