---
id: ticket-025
title: "Import d'un projet local existant (backend)"
type: feat
status: done
priority: high
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-06-21
---

# ticket-025 — Import d'un projet local existant

## Objectif

Permettre d'amener un projet de code existant dans vibe-ide sans le recréer depuis zéro. L'utilisateur pointe vers son dossier, choisit le mode (copie ou symlink), et l'IDE adopte le projet en créant l'arborescence vibe-ide nécessaire autour du code existant.

## Contexte

Aujourd'hui `ProjectLoader` ne scanne que `IDE_WORKSPACE_DIR` et ne peut pas adopter un dossier extérieur. Un utilisateur qui veut utiliser vibe-ide sur son projet React ou son API FastAPI existante doit tout recréer manuellement — c'est un frein majeur à l'adoption.

Deux modes d'import :
- **Symlink** (recommandé) : le dossier reste à son emplacement original, vibe-ide crée un lien symbolique dans `IDE_WORKSPACE_DIR`. Modifications visibles immédiatement des deux côtés.
- **Copie** : le code est copié dans `IDE_WORKSPACE_DIR`. Indépendant de la source.

## Solution proposée

### `backend/src/vibe_ide/services/project_importer.py`

```python
class ProjectImporter:
    def __init__(self, workspace: Path) -> None: ...

    async def import_project(
        self,
        source_path: Path,
        mode: Literal["copy", "symlink"],
        project_id: str | None = None,
    ) -> Project:
        # 1. Valider source_path (existe, est dossier, pas parent du workspace)
        # 2. Résoudre les symlinks pour détecter les boucles
        # 3. project_id = project_id ou source_path.name (sanitisé)
        # 4. Si mode=copy → copie récursive avec exclusions
        #    Si mode=symlink → os.symlink(source_path, workspace/project_id)
        # 5. Créer l'arborescence vibe-ide (tickets/, memory/, workspace/)
        #    sans écraser le code existant
        # 6. Retourner Project via ProjectLoader.load_project()
```

**Exclusions de copie :** `.git`, `node_modules`, `.venv`, `__pycache__`, `*.pyc`, `.DS_Store`, `.env*`

### Endpoint

`POST /api/v1/projects/import`

```json
// Request
{
  "source_path": "/Users/moi/Desktop/mon-projet",
  "mode": "symlink",
  "project_id": "mon-projet"
}

// Response
{ "project": { "id": "mon-projet", "name": "...", ... } }
```

## Critères d'acceptation

- [ ] Un dossier local peut être importé en mode symlink sans déplacer son contenu
- [ ] Un dossier local peut être importé en mode copie (fichiers sensibles exclus)
- [ ] Le projet apparaît dans la sidebar après import, avec ses tickets existants (si dossier `tickets/` présent)
- [ ] Un deuxième import du même projet retourne une erreur claire (pas d'écrasement silencieux)
- [ ] Une tentative d'import du workspace lui-même est refusée avec un message explicite

## Spécifications techniques

**Sécurité critique :**
- `source_path.resolve()` avant toute validation
- Refuser si `source_path` est parent de `IDE_WORKSPACE_DIR` (path traversal)
- Refuser si `source_path` est dans `IDE_WORKSPACE_DIR` (déjà importé)
- Ne jamais copier de fichiers `.env*` (secrets)
- Mode symlink : pointer vers la source, pas copier ses symlinks internes

**Sanitisation du `project_id` :**
```python
re.sub(r"[^a-z0-9-]", "-", source_path.name.lower())[:50]
```

## Dépendances

Aucune dépendance sur d'autres tickets. Pré-requis des tickets 026, 027, 030.

## Estimation

**2j** — Gestion filesystem + sécurité + tests de validation de chemins.

## Risques

- **Élevé** — Opérations filesystem avec risques de path traversal. Tests de sécurité exhaustifs obligatoires.
- **Moyen** — Comportement des symlinks sur Windows (Tauri) non testé.
