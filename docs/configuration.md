# Configuration

Toutes les variables sont dans `.env` (copie de `.env.example`) :

| Variable | Requis | Default | Description |
|----------|--------|---------|-------------|
| `LLM_PROVIDER` | | `agent_sdk` | `agent_sdk` (abonnement Claude) ou `anthropic_api` (crédits API) |
| `ANTHROPIC_API_KEY` | si `anthropic_api` | — | Clef API Anthropic — inutile en mode `agent_sdk` |
| `LLM_MAX_TURNS` | | `30` | Plafond d'allers-retours outil pour un agent (défaut global) |
| `LLM_MAX_TURNS_REVIEWER` | | `10` | Plafond d'actions du reviewer dans la boucle de révision |
| `LLM_MAX_TURNS_PLAN` | | `25` | Plafond d'actions du tour de cadrage (planification de tickets) |
| `LLM_MAX_TURNS_REVIEWER` | | `10` | Plafond d'allers-retours outil pour le reviewer (lecture et critique du diff) |
| `LLM_MAX_TURNS_PLAN` | | `25` | Plafond d'allers-retours outil pour le tour de plan (lecture seule) |
| `LLM_MAX_BUDGET_USD` | | `2.0` | Plafond de dépense d'un seul appel agent. Un dépassement n'est plus une erreur : le run se termine non approuvé et commite son travail (ADR-037) |
| `AGENT_SILENCE_MAX_S` | | `1200` | Délai maximum sans message du flux d'un agent avant interruption du processus (en secondes, ticket-381) |
| `RUN_MAX_BUDGET_USD` | | `5.0` | Plafond cumulé d'un run autonome (`0` = aucun) |
| `CHAT_MAX_CONVERSATION_USD` | | `2.0` | Plafond cumulé d'une conversation du chat |
| `IDE_WORKSPACE_DIR` | | `~/tessera-workspace` | Dossier des projets |
| `IDE_PROMPTS_DIR` | | `agents/prompts/` | Dossier des system prompts |
| `IDE_LOG_LEVEL` | | `INFO` | Niveau de log |
| `GITHUB_TOKEN` | | `""` | Token GitHub (sync issues, clone, PRs) |
| `GITHUB_REPO` | | `""` | Repo cible `owner/repo` |
| `GITHUB_BASE_BRANCH` | | `develop` | Base par défaut des PR ouvertes par l'IDE |
| `DIALOGUE_TIMEOUT_S` | | `300.0` | Délai après lequel un agent qui a posé une question reprend seul, en énonçant son hypothèse (ADR-025) |
| `ATTENTE_FUSIONNABILITE_MAX_S` | | `300` | Délai maximum d'attente pour le calcul du statut fusionnable d'une PR avant abandon de la tentative de merge (en secondes, ticket-384) |
| `ATTENTE_MERGE_MAX_S` | | `600` | Pour les projets avec `merge_without_ci: true`, délai maximum d'attente du merge du ticket précédent avant de lancer le ticket suivant d'une file (en secondes, ticket-382) |
| `AGENT_SILENCE_MAX_S` | | `1200` | Délai maximum (en secondes) d'inactivité avant arrêt d'un agent silencieux. Évite qu'un processus figé ne bloque le run indéfiniment |
| `IDE_DB_PATH` | | `tessera.db` | Base SQLite des runs, coûts et événements |
| `FORBIDDEN_TERMS` | | `""` | Termes interdits au push et en CI, virgules comme séparateurs. Correspondance insensible à la casse, accents normalisés (ADR-048, ADR-050). |
| `OLLAMA_BASE_URL` | | `http://127.0.0.1:11434` | URL du serveur Ollama pour les modèles locaux (rôles de jugement uniquement) |
| `OLLAMA_MAX_CONCURRENT` | | `1` | Nombre maximum de requêtes parallèles au serveur Ollama. Au-delà, les requêtes attendent leur créneau |
| `OLLAMA_SLOT_WAIT_S` | | `30` | Délai maximum d'attente pour un créneau chez le serveur Ollama avant basculement sur le repli (en secondes) |
| `OLLAMA_COOLDOWN_S` | | `600` | Durée du repos du serveur Ollama après un dépassement de délai, avant nouvelle tentative (en secondes) |
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

## Ollama

Quand plusieurs runs lancent des appels au serveur Ollama simultanément, l'IDE les
sérialise pour éviter la compétition pour le modèle et la mémoire. Si le serveur
ne peut pas traiter une requête assez vite, l'IDE bascule automatiquement sur le
repli Claude pour ne pas bloquer le run.

| Variable | Requis | Default | Description |
|----------|--------|---------|-------------|
| `OLLAMA_BASE_URL` | | `http://127.0.0.1:11434` | Adresse du serveur Ollama |
| `OLLAMA_MAX_CONCURRENT` | | `1` | Nombre maximum de requêtes parallèles au serveur Ollama (sérialisation par serveur) |
| `OLLAMA_SLOT_WAIT_S` | | `30` | Délai d'attente maximum pour un créneau disponible. Au-delà, le serveur est considéré saturé et le repli prend le relais (en secondes) |
| `OLLAMA_COOLDOWN_S` | | `600` | Après un dépassement du délai de lecture, le serveur est marqué lent pendant cette durée ; tout appel lève `ProviderIndisponible` aussitôt, sans requête (en secondes) |

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

## MAX_PARALLEL_TEST_RUNS

Par défaut, `2`. Nombre maximum de suites de tests qui peuvent tourner en parallèle sur la machine.

Quand plusieurs files lancent des tests en même temps sur des projets différents, ce réglage les met en file d'attente : seul `MAX_PARALLEL_TEST_RUNS` tests avancent à la fois. Les autres attendent leur créneau. Le log du pipeline affiche « testeur: en attente d'un créneau de test » quand un testeur attend son tour.

Mettre la valeur à `0` ou moins désactive la borne — tous les tests tournent en parallèle, ce qui peut surcharger la machine quand plusieurs files tournent simultanément.

