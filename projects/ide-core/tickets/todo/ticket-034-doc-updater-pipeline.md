---
id: ticket-034
title: "Agent doc-updater — mise à jour automatique de la documentation"
type: feat
status: todo
priority: medium
agent: codeur
depends_on:
  - ticket-021
estimated_days: 1.5
created: 2026-06-21
---

# ticket-034 — Agent doc-updater

## Objectif

Maintenir la documentation à jour automatiquement après chaque approbation de pipeline. Aujourd'hui, le README et les docs vieillissent silencieusement. L'agent `doc-updater` lit le diff produit par le codeur et met à jour uniquement ce qui a changé.

## Contexte

Le pipeline actuel s'arrête à `codeur → reviewer`. Quand un ticket est approuvé, les docs ne reflètent pas les nouveaux endpoints, features ou conventions. Ce ticket ajoute `doc-updater` comme étape optionnelle post-approbation, activable par projet.

### Pipeline cible
```
codeur → reviewer → doc-updater (si enabled)
              ↓
          ticket done
```

## Solution proposée

### `agents/prompts/doc-updater.md`

```markdown
Tu es un expert en documentation technique.
Tu reçois le diff du code approuvé, les docs existants (README.md, docs/),
et le CLAUDE.md du projet.

Mets à jour uniquement ce qui a réellement changé :
- README.md : nouvelles features, endpoints API, commandes
- docs/ : architecture si modifiée
- CLAUDE.md : stack ou conventions si évoluées

Si rien ne change, réponds avec : { "no_changes": true }

Sinon, réponds avec :
{
  "files": [
    { "path": "README.md", "content": "..." }
  ]
}
```

### `backend/src/vibe_ide/services/doc_updater.py`

```python
@dataclass
class DocUpdateResult:
    files_updated: list[str]
    no_changes: bool

class DocUpdaterService:
    async def update_docs(
        self,
        project_path: Path,
        diff: str,
        ticket: Ticket,
    ) -> DocUpdateResult:
        # 1. Lire README.md, docs/*.md, CLAUDE.md (tronqués à 8k chacun)
        # 2. Appeler Claude avec doc-updater.md
        # 3. Extraire JSON via utils.json_extract
        # 4. Si no_changes → retourner sans écriture
        # 5. Écrire les fichiers modifiés
        # 6. Retourner DocUpdateResult
```

### Intégration dans `OrchestratorService`

```python
if pipeline_config.doc_updater_enabled and result.approved:
    doc_result = await doc_updater.update_docs(
        project_path, result.diff, ticket
    )
    await emit_ws("doc_updated", { "files": doc_result.files_updated })
```

### Activation par projet (`agents.json`)

```json
{ "pipeline": { "doc_updater_enabled": false } }
```

### WS Event

`doc_updated` : `{ "files_updated": ["README.md"] }` — affiché dans `AgentPanel`.

## Critères d'acceptation

- [ ] Après approbation, `README.md` est mis à jour si le diff contient un nouvel endpoint
- [ ] `{ "no_changes": true }` → aucun fichier écrit, aucune modification du projet
- [ ] L'event WS `doc_updated` apparaît dans l'`AgentPanel` après le reviewer
- [ ] Désactivé par défaut (`doc_updater_enabled: false`) — aucun impact sur les projets existants

## Spécifications techniques

Le `diff` passé à l'agent est le résumé du code produit par le codeur (contenu de `AgentResult.content`), pas un diff git réel (la gestion git est hors scope pour v0).

Limite contexte : tronquer chaque doc à 8k caractères. Si README > 8k, inclure l'en-tête + les 4 dernières sections.

## Dépendances

- **ticket-021** — `utils/json_extract` pour l'extraction JSON.

## Estimation

**1.5j** — Service doc + intégration orchestrateur + prompt engineering + tests.

## Risques

- **Moyen** — L'agent peut modifier des sections qui ne devraient pas l'être si le diff est mal délimité. Le prompt doit être très explicite sur "modifier uniquement ce qui a changé".
