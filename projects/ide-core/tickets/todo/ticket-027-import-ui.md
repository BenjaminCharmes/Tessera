---
id: ticket-027
title: "UI import de projet existant"
type: feat
status: todo
priority: high
agent: codeur
depends_on:
  - ticket-025
  - ticket-026
estimated_days: 2
created: 2026-06-21
---

# ticket-027 — UI import de projet existant

## Objectif

Exposer le workflow d'import et d'analyse dans une interface en 3 étapes : l'utilisateur saisit le chemin de son projet, patiente pendant l'analyse, puis valide le `CLAUDE.md` généré avant de démarrer. Si un agent suggéré n'existe pas, il peut le créer directement depuis cette modale.

## Contexte

Les endpoints d'import (ticket-025) et d'analyse (ticket-026) existent en backend. Ce ticket crée l'interface frontend qui orchestre les deux appels et présente les résultats de manière actionnable. Point d'intégration clé : si `project-analyzer` suggère `redacteur` mais que l'agent n'existe pas dans le registre, l'utilisateur doit pouvoir le créer sans quitter le flux.

## Solution proposée

### `frontend/src/components/Sidebar/ImportProjectModal.tsx`

**Étape 1 — Chemin source**
```
Chemin du dossier : [/Users/moi/Desktop/mon-projet  ]
Mode : ● Symlink (recommandé)  ○ Copie
                               [Importer →]
```

**Étape 2 — Analyse en cours**
```
Import et analyse du projet…
[████████░░] 60%
Détection de la stack TypeScript, React…
```

**Étape 3 — Validation**
```
✅ mon-projet importé

CLAUDE.md généré :
┌─────────────────────────────────────┐
│ # CLAUDE.md — mon-projet            │
│ Stack : TypeScript, React, Vite     │
│ Agents : codeur, reviewer           │
└─────────────────────────────────────┘

Stack détectée : TypeScript, React
Agents suggérés : codeur ✅  reviewer ✅  testeur ⚠ absent
                                           [→ Créer l'agent testeur]

[Modifier le CLAUDE.md]  [Valider et ouvrir]
```

Si agent absent → ouvre `AgentCreatorModal` (ticket-024) pré-rempli avec le nom.

### Modifications `ProjectNav.tsx`

Ajouter un bouton "↓ Importer un projet" en dessous de "+ Créer un projet".

### Types et API client

```typescript
// types/api.ts
export interface ImportProjectRequest {
  source_path: string;
  mode: "copy" | "symlink";
  project_id?: string;
}

export interface AnalysisResult {
  claude_md: string;
  detected_stack: string[];
  suggested_agents: string[];
  claude_md_written: boolean;
}
```

```typescript
// lib/api.ts
projects: {
  ...existing,
  import: (req: ImportProjectRequest): Promise<Project> =>
    post("/projects/import", req),
  analyze: (projectId: string, overwrite = false): Promise<AnalysisResult> =>
    post(`/projects/${projectId}/analyze`, { overwrite }),
},
```

## Critères d'acceptation

- [ ] L'utilisateur peut importer un dossier local en 3 étapes depuis la sidebar
- [ ] Le `CLAUDE.md` généré est affiché et modifiable avant validation
- [ ] Les agents absents du registre sont clairement signalés avec un lien vers `AgentCreatorModal`
- [ ] Un import échoué affiche un message d'erreur actionnable (chemin invalide, déjà importé…)
- [ ] Après validation, le projet apparaît immédiatement dans la liste et la sidebar passe sur ses tickets

## Spécifications techniques

État de la modale : `"idle" | "importing" | "analyzing" | "review" | "error"`

Le bouton "Valider" appelle `onProjectCreated(project)` → ferme la modale + navigue vers le panel tickets.

## Dépendances

- **ticket-025** — Endpoint `POST /projects/import`.
- **ticket-026** — Endpoint `POST /projects/{id}/analyze`.
- **ticket-024** — `AgentCreatorModal` pour créer les agents manquants.

## Estimation

**2j** — UI multi-étapes + intégration AgentCreatorModal + tests RTL.

## Risques

- **Moyen** — L'analyse peut être longue (10-20s). Prévoir un timeout UI et un message si le backend ne répond pas.
