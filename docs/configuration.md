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
| `FORBIDDEN_TERMS` | | `""` | Termes interdits au push et en CI, virgules comme séparateurs. Correspondance insensible à la casse, accents normalisés (ADR-048, ADR-050). |
| `STATIC_TOKEN` | | `""` | Si renseignée, **toutes** les requêtes — HTTP et WebSocket — exigent le token (voir ci-dessous). Vide, l'API est ouverte : `make dev` et `make run` ne la servent que sur `127.0.0.1` |

## `STATIC_TOKEN`

Renseigné, le token protège chaque route, `OPTIONS` (préflight CORS) et
`/health` exceptés :

- **HTTP** : en-tête `Authorization: Bearer <token>`, sinon `401` ;
- **WebSocket** : le même en-tête, ou `?token=<token>` dans l'URL — un
  navigateur ne peut pas poser d'en-tête sur `new WebSocket(url)`. Sans
  token valide, la connexion est fermée avec le code `4401`.

Le frontend lit la même valeur dans `frontend/.env.local` :

```bash
VITE_STATIC_TOKEN=<token>
```

Sans elle, une UI face à un backend protégé ne reçoit que des `401`.

**À savoir** : passé en `?token=`, le token apparaît dans les logs d'accès
uvicorn et dans tout proxy sur le chemin. Le Bearer HTTP n'y apparaît pas.
`VITE_STATIC_TOKEN` est inliné dans le bundle : c'est un secret partagé
entre le poste et son backend, pas un mécanisme de comptes.

## Application desktop (Tauri)

Le frontend packagé est servi depuis `tauri://localhost`, où rien ne répond
sur `/api/v1` : l'origine du backend est figée **au build** par Vite.

| Variable | Où | Default | Description |
|----------|----|---------|-------------|
| `VITE_API_URL` | `frontend/.env.production` | `http://127.0.0.1:8000` | Origine du backend pour les appels REST, WebSocket et fichiers. Vide en dev : les URL restent relatives et le proxy Vite les résout |
| `TESSERA_BACKEND_DIR` | environnement de l'app | `../../backend` (résolu à la compilation) | Dossier depuis lequel l'app release lance `uv run uvicorn … --host 127.0.0.1`. À renseigner dès que l'app ne vit plus à côté de ses sources |

Le shell desktop n'a aucune commande fichier à lui : tout accès disque passe
par `routers/fs.py`, qui refuse les chemins hors workspace (ADR-040). Le
backend Python n'est pas embarqué dans le bundle : la machine doit avoir `uv`.

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
