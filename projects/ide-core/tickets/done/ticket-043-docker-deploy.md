---
id: ticket-043
title: "Docker Compose + déploiement cloud"
type: chore
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-07-13
---

# ticket-043 — Docker Compose et déploiement cloud

## Objectif

Permettre de lancer vibe-ide sur n'importe quelle machine (ou serveur cloud)
avec une seule commande : `docker compose up`.

## Contexte

Actuellement le projet nécessite Python/uv + Node.js + Rust installés localement,
et deux terminaux (ou `make run`). Pour un usage sur serveur ou partage de l'IDE
avec une autre machine personnelle, Docker simplifie drastiquement le setup.

## Solution proposée

### Dockerfiles

- **`backend/Dockerfile`** — image Python 3.11-slim, copie le code, `uv pip install`,
  expose le port 8000, `CMD uvicorn vibe_ide.main:app`
- **`frontend/Dockerfile`** — build multi-stage : stage Node pour `npm run build`,
  stage Nginx pour servir le dist statique sur le port 80

### docker-compose.yml (racine)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./projects:/app/projects   # workspace persisté
      - ./agents/prompts:/app/prompts
      - vibe-data:/app/data        # SQLite

  frontend:
    build: ./frontend
    ports: ["5173:80"]
    depends_on: [backend]

volumes:
  vibe-data:
```

### Protection minimale (optionnelle, activée si `STATIC_TOKEN` défini dans `.env`)

Un middleware FastAPI qui vérifie `Authorization: Bearer <token>` si la variable
`STATIC_TOKEN` est définie — silencieusement ignoré si absente. 0 breaking change
pour l'usage local.

### Documentation

Mettre à jour `README.md` avec la section "Lancement via Docker".

## Critères d'acceptation

- [ ] `docker compose up` lance backend + frontend sans erreur
- [ ] L'UI est accessible sur http://localhost:5173
- [ ] Le workspace (`projects/`) et la base SQLite survivent à un `docker compose down`
- [ ] Le README documente la procédure Docker
- [ ] Si `STATIC_TOKEN` est défini dans `.env`, l'API le vérifie sur tous les endpoints

## Dépendances

Aucune.

## Estimation

**1j** — Dockerfiles + compose + middleware token optionnel + doc.

## Risques

- **Faible** — Le build frontend doit pointer sur l'URL backend correcte
  (variable d'env `VITE_API_URL` à injecter au build ou au runtime via Nginx config).
