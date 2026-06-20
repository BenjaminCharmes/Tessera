---
id: ticket-004
title: Agent Project Creator
type: feat
status: done
priority: high
agent: codeur
depends_on: [ticket-003]
created: 2025-06
---

# ticket-004 — Agent Project Creator

## Contexte

Le Project Creator est l'agent qui permet à l'IDE de bootstrapper
de nouveaux projets via une conversation guidée.
C'est la première feature "utilisateur" de l'IDE.

## Tâche

### Flow de création de projet

```
User: "Je veux créer un projet pour mon potager"

Project Creator:
  1. Pose 4-5 questions (nom, type, langue, domaine, agents utiles)
  2. Génère le CLAUDE.md adapté
  3. Appelle POST /api/v1/projects pour créer la structure
  4. Propose les premiers tickets à créer
  5. Retourne un résumé du projet créé
```

### Prompt système (`agents/prompts/project-creator.md`)

Le prompt est déjà écrit dans `agents/prompts/` — le codeur n'a pas à l'inventer.

### Endpoint dédié

```
POST /api/v1/agents/create-project
Body: {
  "conversation": [
    {"role": "user", "content": "Je veux un projet jardinage"},
    {"role": "assistant", "content": "..."},
    ...
  ]
}
Response: {
  "project": Project,
  "suggested_tickets": list[TicketDraft],
  "claude_md_generated": str
}
```

### Mode "one-shot" vs "conversation"

- **One-shot** : l'utilisateur fournit un brief complet, l'agent crée directement
- **Conversation** : l'agent pose des questions, l'UI gère le multi-tour

Implémenter les deux. Le one-shot est plus simple, commencer par lui.

### `TicketDraft` (nouveau modèle)

```python
class TicketDraft(BaseModel):
    title: str
    type: TicketType
    priority: TicketPriority
    agent: str
    description: str   # pas encore un vrai ticket, juste une suggestion
```

## Critères d'acceptation

- [ ] `POST /api/v1/agents/create-project` avec un brief simple crée un projet valide
- [ ] Le CLAUDE.md généré contient les sections standard (Stack, Agents actifs, Conventions)
- [ ] 3-5 tickets de démarrage sont suggérés et cohérents avec le projet
- [ ] Le projet créé apparaît dans `GET /api/v1/projects`
- [ ] Test avec brief "projet jardinage méditerranéen" produit des agents pertinents (pas de codeur)

## Notes

- Le Project Creator appelle Claude pour générer le CLAUDE.md — pas de template hardcodé
- Il doit adapter les agents suggérés au type de projet (technique vs non-technique)
- Garder une trace de la conversation dans `memory/project-creation-log.md` du nouveau projet
