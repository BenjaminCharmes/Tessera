# Configuration

Toutes les variables sont dans `.env` (copie de `.env.example`) :

| Variable | Requis | Default | Description |
|----------|--------|---------|-------------|
| `LLM_PROVIDER` | | `agent_sdk` | `agent_sdk` (abonnement Claude) ou `anthropic_api` (crédits API) |
| `ANTHROPIC_API_KEY` | si `anthropic_api` | — | Clef API Anthropic — inutile en mode `agent_sdk` |
| `LLM_MAX_TURNS` | | `30` | Plafond d'allers-retours outil pour un agent |
| `LLM_MAX_BUDGET_USD` | | `2.0` | Plafond de dépense d'un seul appel agent. Un dépassement n'est plus une erreur : le run se termine non approuvé et commite son travail (ADR-037) |
| `RUN_MAX_BUDGET_USD` | | `5.0` | Plafond cumulé d'un run autonome (`0` = aucun) |
| `CHAT_MAX_CONVERSATION_USD` | | `2.0` | Plafond cumulé d'une conversation du chat |
| `IDE_WORKSPACE_DIR` | | `~/tessera-workspace` | Dossier des projets |
| `IDE_PROMPTS_DIR` | | `agents/prompts/` | Dossier des system prompts |
| `IDE_LOG_LEVEL` | | `INFO` | Niveau de log |
| `GITHUB_TOKEN` | | `""` | Token GitHub (sync issues, clone, PRs) |
| `GITHUB_REPO` | | `""` | Repo cible `owner/repo` |
| `GITHUB_BASE_BRANCH` | | `develop` | Base par défaut des PR ouvertes par l'IDE |
| `DIALOGUE_TIMEOUT_S` | | `300.0` | Délai après lequel un agent qui a posé une question reprend seul, en énonçant son hypothèse (ADR-025) |
| `IDE_DB_PATH` | | `tessera.db` | Base SQLite des runs, coûts et événements |
| `STATIC_TOKEN` | | `""` | Si renseignée, **toutes** les requêtes API exigent `Authorization: Bearer <token>`. Vide, l'API est ouverte : ne l'exposer que sur une interface de confiance |

## Commandes de développement

```bash
make setup         # Initialisation complète (première fois)
make dev           # Lance FastAPI sur http://localhost:8000
make dev-frontend  # Lance Vite sur http://localhost:5173
make tauri-dev     # Lance l'app desktop Tauri (nécessite make dev)
make tauri-build   # Build production (.app distributable)
make test          # Tests Python (pytest)
make test-fast     # Tests Python rapides
make test-coverage # Rapport de couverture backend + frontend
make lint          # Type-check mypy
make clean         # Supprime les caches
```

Tests frontend :

```bash
cd frontend
npm run test          # Vitest unit tests
npm run test:coverage # Rapport de couverture
npm run test:e2e      # Playwright E2E (5 flows, nécessite npm run dev)
```
