---
id: ticket-030
title: "Clone de repo GitHub dans le workspace"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on:
  - ticket-025
  - ticket-026
estimated_days: 1.5
created: 2026-06-21
---

# ticket-030 — Clone de repo GitHub

## Objectif

Permettre d'importer un repo GitHub directement par URL, sans passer par un clone manuel. L'IDE clone, analyse automatiquement le code (ticket-026), et est prêt à travailler en quelques secondes.

## Contexte

Ticket-025 couvre l'import d'un dossier local. Ce ticket complète le workflow pour les repos GitHub : cloner dans `IDE_WORKSPACE_DIR`, stocker le remote associé, et lancer l'analyse automatique. C'est le point d'entrée principal pour les nouveaux utilisateurs qui veulent utiliser vibe-ide sur un projet GitHub existant.

## Solution proposée

### `backend/src/vibe_ide/services/git_clone.py`

```python
class GitCloneService:
    CLONE_TIMEOUT = 60  # secondes

    async def clone(
        self,
        repo_url: str,
        project_id: str | None = None,
        github_token: str | None = None,
    ) -> CloneResult:
        # 1. Valider l'URL (pattern https://github.com/owner/repo)
        # 2. Construire l'URL auth : https://token@github.com/owner/repo
        # 3. asyncio.create_subprocess_exec("git", "clone", "--depth=1", url, dest)
        #    Timeout 60s. Jamais shell=True.
        # 4. Nettoyer dest en cas d'erreur (shutil.rmtree)
        # 5. Stocker github_remote dans agents.json
        # 6. Enchaîner ProjectAnalyzerService.analyze()

@dataclass
class CloneResult:
    project: Project
    claude_md_generated: bool
    detected_stack: list[str]
```

### Endpoint

`POST /api/v1/projects/clone`

```json
// Request
{
  "repo_url": "https://github.com/owner/mon-projet",
  "project_id": "mon-projet"
}

// Response
{
  "project": { "id": "mon-projet", "github_remote": "https://github.com/owner/mon-projet", ... },
  "claude_md_generated": true,
  "detected_stack": ["Python", "FastAPI"]
}
```

### Modèle `Project` enrichi

Ajouter `github_remote: str | None` dans le modèle `Project` et dans `agents.json`.

### Frontend

Option "Cloner depuis GitHub" dans `ImportProjectModal` (ticket-027) : choisir entre dossier local et repo GitHub avant l'étape 1. Si GitHub, champ URL à la place du chemin.

Badge GitHub dans `ProjectNav.tsx` : si `github_remote` est défini, afficher un lien cliquable vers le repo.

## Critères d'acceptation

- [ ] Un repo GitHub public peut être cloné par URL sans configuration supplémentaire
- [ ] Un repo privé peut être cloné avec un token GitHub (via settings de l'IDE)
- [ ] Le `github_remote` est stocké et affiché comme badge dans la sidebar
- [ ] Un clone échoué nettoie proprement le dossier cible (pas de dossier vide orphelin)
- [ ] Une URL invalide retourne une erreur explicite avant tout appel git

## Spécifications techniques

**Sécurité critique :**
- Valider l'URL avec regex stricte : `^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$`
- Ne jamais loguer le token ou l'URL avec token
- `--depth=1` : historique minimal
- Timeout 60s sur le subprocess git

Cleanup sur erreur :
```python
try:
    await clone_subprocess(...)
except Exception:
    shutil.rmtree(dest, ignore_errors=True)
    raise
```

## Dépendances

- **ticket-025** — `ProjectImporter` pour créer l'arborescence vibe-ide post-clone.
- **ticket-026** — `ProjectAnalyzerService` pour générer le `CLAUDE.md`.

## Estimation

**1.5j** — Service subprocess sécurisé + intégration analyze + frontend badge + tests.

## Risques

- **Élevé** — Injection via `repo_url`. La validation regex est obligatoire avant toute exécution.
- **Moyen** — Clone lent sur les gros repos (même avec `--depth=1`). Timeout et feedback UI nécessaires.
