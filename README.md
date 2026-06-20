# vibe-ide

IDE multi-projets avec orchestration d'agents IA.
Se construit lui-même via le projet `ide-core`.

## Démarrage rapide

```bash
# Prérequis : Claude Code installé, ANTHROPIC_API_KEY dans l'env

# 1. Ouvrir ce dossier dans Claude Code
cd vibe-ide
claude .

# 2. Claude Code lira CLAUDE.md automatiquement
# 3. Demander à Claude Code de commencer par ticket-000 :
#    "Implémente le ticket-000"
```

## Structure

```
vibe-ide/
  CLAUDE.md                    ← Constitution principale (lire en premier)
  projects/
    ide-core/                  ← L'IDE se construit lui-même
      CLAUDE.md                ← Contexte du projet bootstrap
      agents.json              ← Agents actifs et config
      tickets/
        todo/                  ← Tickets à faire (commencer par ticket-000)
        in-progress/
        done/
      memory/
        decisions.md           ← Décisions d'architecture
        stack.md               ← Référence technique
  agents/
    prompts/                   ← System prompts de chaque agent
      orchestrateur.md
      codeur.md
      reviewer.md
      architect.md
      project-creator.md
  docs/
    architecture.md            ← Vue d'ensemble technique
  backend/                     ← (créé par ticket-000)
  frontend/                    ← (créé plus tard)
```

## Ordre d'implémentation

| Ticket | Description | Crée |
|--------|-------------|------|
| ticket-000 | Structure backend | `backend/` complet |
| ticket-001 | Modèles + service tickets | CRUD tickets |
| ticket-002 | Project loader | Chargement CLAUDE.md |
| ticket-003 | Agent loop | Appels Anthropic SDK |
| ticket-004 | Project Creator | Nouveaux projets via agent |
| ticket-005 | Orchestrateur | Pipeline codeur→reviewer |

## Philosophie

- **Self-hosting** : l'IDE se construit lui-même
- **Tickets = fichiers Markdown** : pas de DB, versionnables, lisibles sans l'IDE
- **Agents découplés** : chaque agent a un prompt, l'orchestrateur gère le routing
- **Couches séparées** : UI / orchestration / agents / filesystem sont indépendants
