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
- Organisation par statut : `todo/`, `in-progress/`, `done/`, `archive/`
- Lisibles sans l'IDE (plain text dans le repo)
- Champ optionnel `github_issue_url` pour tracer l'origine GitHub

---

## Workflow

```
GitHub Issue (humain)
        │
        │  labelisé "agent-ready"
        ▼
  agent github-sync (ticket-006)
        │
        │  génère automatiquement
        ▼
tickets/todo/ticket-XXX.md  ←─── source de vérité agent
        │
        │  orchestrateur + agents
        ▼
  in-progress → done → archive
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

## Agent github-sync (à venir — ticket-006)

Rôle : poll les GitHub Issues labelisées `agent-ready` et crée les fichiers
Markdown correspondants dans `tickets/todo/`.

Déclenchement : périodique (cron) ou webhook GitHub.

Champs mappés :

| GitHub Issue       | Frontmatter Markdown     |
|--------------------|--------------------------|
| title              | title                    |
| body               | corps Markdown           |
| labels             | type (feat/fix/chore…)   |
| URL                | github_issue_url         |
| —                  | status: todo             |
| —                  | agent: orchestrateur     |
