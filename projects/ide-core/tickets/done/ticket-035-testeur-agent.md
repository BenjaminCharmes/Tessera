---
id: ticket-035
title: "Agent testeur — exécution automatique des tests dans le pipeline"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on:
  - ticket-021
estimated_days: 1.5
created: 2026-06-21
---

# ticket-035 — Agent testeur

## Objectif

Donner au reviewer des données objectives : résultats de tests réels (pass/fail, coverage) produits automatiquement après chaque cycle codeur. Le reviewer n'a plus à deviner si le code fonctionne — il sait.

## Contexte

Aujourd'hui le reviewer lit le code mais n'exécute rien. Ce ticket ajoute `testeur` entre codeur et reviewer : il lance la suite de tests du projet, analyse les résultats, et passe le rapport au reviewer comme contexte supplémentaire.

### Pipeline cible
```
codeur → testeur → reviewer → [doc-updater]
           ↓
   TestResult { passed, total, failed, output_summary }
```

## Solution proposée

### `agents/prompts/testeur.md`

```markdown
Tu es un agent d'exécution et d'analyse de tests.
Tu reçois le code produit et la commande de test du projet.

1. Identifie la commande de test (depuis CLAUDE.md ou auto-détection)
2. Analyse le résultat (pass/fail, nombre, erreurs)

Réponds avec ce JSON :
{
  "passed": true,
  "total": 42,
  "failed": 0,
  "output_summary": "42 passed in 3.2s",
  "errors": []
}
```

### `backend/src/vibe_ide/services/test_runner.py`

```python
@dataclass
class TestResult:
    passed: bool
    total: int
    failed: int
    output_summary: str
    errors: list[str]
    duration_ms: int

class TestRunnerService:
    TIMEOUT = 120  # secondes

    async def run_tests(
        self,
        project_path: Path,
        test_command: str | None = None,
    ) -> TestResult:
        # 1. Auto-détecter : pyproject.toml → "uv run pytest",
        #    package.json → "npm test", Cargo.toml → "cargo test"
        # 2. asyncio.create_subprocess_exec (jamais shell=True)
        # 3. Timeout 120s
        # 4. Parser stdout/stderr → TestResult
```

### Intégration dans `OrchestratorService`

```python
if pipeline_config.testeur_enabled:
    test_result = await test_runner.run_tests(project_path)
    # Injecter test_result dans le contexte du reviewer
    await emit_ws("test_result", test_result.__dict__)
```

Le reviewer reçoit le rapport de tests comme contexte additionnel : si des tests échouent, il doit demander des corrections au codeur.

### Activation (`agents.json`)

```json
{
  "pipeline": {
    "testeur_enabled": true,
    "test_command": "uv run pytest"
  }
}
```

### WS Event

`test_result` : `{ passed, total, failed, output_summary }`.
Badge dans `TicketCard` : `✅ 42/42` ou `❌ 3/42` pendant l'exécution.

## Critères d'acceptation

- [ ] Un projet Python avec pytest : la commande est auto-détectée et lancée
- [ ] Un projet Node.js avec `package.json` : `npm test` est lancé
- [ ] Si les tests échouent, le reviewer reçoit le rapport d'erreurs dans son contexte
- [ ] L'event WS `test_result` apparaît dans l'AgentPanel
- [ ] Désactivé par défaut — aucun impact sur les pipelines existants

## Spécifications techniques

**Sécurité :** subprocess sans `shell=True`, timeout 120s, working directory = `project_path`.

**Auto-détection de la commande :**
```python
if (project_path / "pyproject.toml").exists():  return "uv run pytest"
if (project_path / "package.json").exists():    return "npm test"
if (project_path / "Cargo.toml").exists():      return "cargo test"
raise TestCommandNotFound("Impossible de détecter la commande de test")
```

## Dépendances

- **ticket-021** — `AgentRegistryService` (l'agent testeur a un rôle enregistré).

## Estimation

**1.5j** — Service subprocess + auto-détection + intégration orchestrateur + tests.

## Risques

- **Moyen** — Les tests du projet peuvent être lents (> 2min). Timeout à 120s, avec message d'avertissement dans le rapport.
- **Moyen** — Sécurité du subprocess : ne jamais utiliser `shell=True`, valider que `project_path` est dans le workspace.
