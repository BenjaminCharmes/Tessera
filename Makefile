.PHONY: help setup dev dev-frontend tauri-dev tauri-build test lint clean

# ─────────────────────────────────────────────────────────────────────────────
# vibe-ide — Makefile
# ─────────────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make setup        — Initialise l'environnement (copie .env.example, installe deps)"
	@echo "  make dev          — Lance le serveur FastAPI en mode reload (port 8000)"
	@echo "  make dev-frontend — Lance Vite en mode dev (port 5173)"
	@echo "  make tauri-dev    — Lance l'app Tauri (desktop) — nécessite 'make dev' dans un autre terminal"
	@echo "  make tauri-build  — Bundle de production Tauri"
	@echo "  make test         — Lance la suite de tests"
	@echo "  make lint         — Type-check avec mypy"
	@echo "  make clean        — Supprime les artefacts de build et cache"
	@echo ""

setup:
	@[ -f .env ] || cp .env.example .env
	@echo "→ .env créé. Ouvre-le et ajoute ta ANTHROPIC_API_KEY."
	cd backend && uv sync --extra dev
	cd frontend && npm install

dev:
	@echo "→ Serveur démarré sur http://localhost:8000"
	@echo "→ Swagger UI : http://localhost:8000/docs"
	cd backend && uv run uvicorn vibe_ide.main:app \
		--reload \
		--host 0.0.0.0 \
		--port 8000 \
		--env-file ../.env

dev-frontend:
	cd frontend && npm run dev

tauri-dev:
	@echo "→ Lancement de vibe-ide en mode desktop (Tauri)"
	@echo "→ Assure-toi que 'make dev' tourne dans un autre terminal (FastAPI sur :8000)"
	cd frontend && npm run tauri-dev

tauri-build:
	@echo "→ Build production Tauri"
	cd frontend && npm run tauri-build

test:
	cd backend && uv run pytest -v

test-fast:
	cd backend && uv run pytest -q

test-coverage:
	@echo "→ Backend coverage"
	cd backend && uv run pytest -q -m "not integration" --cov=vibe_ide --cov-report=term-missing --cov-report=html:htmlcov
	@echo "→ Frontend coverage"
	cd frontend && npm run test:coverage

lint:
	cd backend && uv run mypy src/

clean:
	find . -type d -name "__pycache__" -not -path "*/.venv/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -not -path "*/.venv/*" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.mypy_cache
	rm -rf frontend/dist frontend/.vite
