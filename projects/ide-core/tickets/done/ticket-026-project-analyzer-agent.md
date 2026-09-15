---
id: ticket-026
title: "Agent project-analyzer — génération CLAUDE.md depuis le code"
type: feat
status: done
priority: high
agent: codeur
depends_on:
  - ticket-025
estimated_days: 1.5
created: 2026-06-21
---

# ticket-026 — Agent project-analyzer

## Objectif

Après import d'un projet existant, générer automatiquement le `CLAUDE.md` en analysant le code. L'utilisateur n'a pas à décrire sa stack ou ses conventions — l'agent les détecte et propose une configuration prête à l'emploi.

## Contexte

Un projet importé via ticket-025 n'a pas encore de `CLAUDE.md`. Sans lui, les agents ne savent pas comment travailler : pas de stack connue, pas de conventions, pas de liste d'agents recommandés. Ce ticket crée l'agent `project-analyzer` qui lit le code et génère ce document fondateur.

Contrainte majeure : ne jamais envoyer de secrets (`.env`, clés API) à l'API Claude. Tronquer les fichiers volumineux pour rester dans les limites de contexte.

## Solution proposée

### `agents/prompts/project-analyzer.md`

```markdown
Tu es un expert en analyse de projets logiciels.
On te fournit l'arbre de fichiers et le contenu des fichiers clés.

Génère un CLAUDE.md complet avec :
- Nom et description du projet
- Stack technique détectée (langages, frameworks, outils)
- Agents actifs recommandés (parmi : codeur, reviewer, architect)
- Conventions de code observées
- Structure des dossiers

Réponds uniquement avec ce JSON :
{
  "claude_md": "# CLAUDE.md — nom\n...",
  "detected_stack": ["Python", "FastAPI"],
  "suggested_agents": ["codeur", "reviewer"]
}
```

### `backend/src/vibe_ide/services/project_analyzer.py`

```python
class ProjectAnalyzerService:
    MAX_FILES = 50
    MAX_FILE_BYTES = 8_000
    EXCLUDED = {".git", "node_modules", ".venv", "__pycache__"}
    SENSITIVE = {".env", ".env.local", "*.key", "*.pem", "secrets*"}
    KEY_FILES = {"README.md", "CLAUDE.md", "package.json", "pyproject.toml",
                 "Cargo.toml", "go.mod", "requirements.txt", "Makefile"}

    async def analyze(
        self,
        project_path: Path,
        overwrite: bool = False,
    ) -> AnalysisResult:
        # 1. Lister l'arbre (max 2 niveaux, exclure EXCLUDED + SENSITIVE)
        # 2. Lire KEY_FILES en priorité + quelques fichiers source
        # 3. Tronquer chaque fichier à MAX_FILE_BYTES
        # 4. Appeler Claude avec project-analyzer.md
        # 5. Extraire JSON via utils.json_extract
        # 6. Écrire CLAUDE.md seulement si absent (ou overwrite=True)
        # 7. Retourner AnalysisResult
```

### Endpoint

`POST /api/v1/projects/{project_id}/analyze`

```json
// Request (optionnel)
{ "overwrite": false }

// Response
{
  "claude_md": "# CLAUDE.md — ...",
  "detected_stack": ["TypeScript", "React"],
  "suggested_agents": ["codeur", "reviewer"],
  "claude_md_written": true
}
```

## Critères d'acceptation

- [ ] Un projet Python avec `pyproject.toml` → stack `["Python"]` détectée
- [ ] Un projet React avec `package.json` → stack `["TypeScript", "React"]` détectée
- [ ] `CLAUDE.md` non écrasé si déjà présent (sans flag `overwrite`)
- [ ] Aucun fichier `.env*` ou `*.key` transmis à l'API Claude
- [ ] Le `CLAUDE.md` généré contient les agents recommandés et la structure du projet

## Spécifications techniques

```python
@dataclass
class AnalysisResult:
    claude_md: str
    detected_stack: list[str]
    suggested_agents: list[str]
    claude_md_written: bool
```

**Limite contexte :** viser < 50k tokens. Si le projet est trop grand, prioriser les fichiers racine et les fichiers de config.

**Détection binaire :** skip les fichiers avec `\x00` dans les premiers 512 octets.

## Dépendances

- **ticket-025** — L'analyse s'applique à un projet déjà importé dans le workspace.

## Estimation

**1.5j** — Service LLM + sampling intelligent + filtrage sécurité + tests.

## Risques

- **Moyen** — Qualité de l'analyse dépend de la diversité des projets testés. Prévoir des cas de test variés (Python, TypeScript, Rust).
- **Faible** — Dépassement du contexte LLM sur de très gros projets. La troncature et la prioritisation atténuent ce risque.
