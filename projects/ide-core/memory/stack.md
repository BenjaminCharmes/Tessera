# Stack technique — référence rapide

## Versions cibles

| Outil | Version | Rôle |
|-------|---------|------|
| Python | 3.11+ | Backend, agents |
| FastAPI | 0.111+ | API orchestrateur |
| Anthropic SDK | latest | Appels Claude |
| uv | latest | Gestionnaire paquets Python |
| Node.js | 20 LTS | Tooling frontend |
| TypeScript | 5.x | Frontend |
| React | 18.x | UI |
| Tauri | 2.x | Shell desktop |
| Vite | 5.x | Bundler frontend |
| SQLite | 3.x | Persistence locale |

## Commandes de base

```bash
# Backend
cd backend/
uv sync                    # installer les dépendances
uv run fastapi dev         # lancer en dev
uv run pytest              # lancer les tests

# Frontend
cd frontend/
npm install
npm run dev                # lancer en dev
npm run build              # build production

# IDE complet (Tauri)
npm run tauri dev          # lancer l'app desktop
```

## Variables d'environnement requises

```bash
ANTHROPIC_API_KEY=sk-ant-...     # obligatoire
IDE_DATA_DIR=~/.tessera/data    # dossier de données (défaut: ~/.tessera/data)
IDE_LOG_LEVEL=INFO               # DEBUG | INFO | WARNING | ERROR
```

## Ports locaux

| Service | Port |
|---------|------|
| Orchestrateur FastAPI | 8765 |
| Frontend Vite dev | 5173 |
| WebSocket agents | 8766 |
