.PHONY: help setup doctor dev dev-frontend tauri-dev tauri-build run run-windows stop test lint clean

# ─────────────────────────────────────────────────────────────────────────────
# Tessera — Makefile
# ─────────────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make setup        — Initialise l'environnement (copie .env.example, installe deps)"
	@echo "  make doctor       — Vérifie les prérequis avant de lancer (à faire en premier)"
	@echo "  make run          — Lance backend + frontend en parallèle (Ctrl+C pour tout arrêter)"
	@echo "  make run-windows  — Idem, mais adapté à Windows (make run utilise trap/wait POSIX)"
	@echo "  make stop         — Arrête backend et frontend, worker --reload orphelin compris"
	@echo "  make dev          — Lance uniquement le serveur FastAPI en mode reload (port 8000)"
	@echo "  make verify       — Tout ce que la CI vérifie, en local (à faire avant de merger)"
	@echo "  make dev-frontend — Lance uniquement Vite en mode dev (port 5173)"
	@echo "  make tauri-dev    — Lance l'app Tauri (desktop) — nécessite 'make dev' dans un autre terminal"
	@echo "  make tauri-build  — Bundle de production Tauri (backend auto-démarré par l'app)"
	@echo "  make test         — Lance la suite de tests"
	@echo "  make lint         — Type-check avec mypy"
	@echo "  make clean        — Supprime les artefacts de build et cache"
	@echo ""

setup:
	@[ -f .env ] || cp .env.example .env
	@echo "→ .env créé. Ouvre-le et ajoute ta ANTHROPIC_API_KEY."
	cd backend && uv sync --extra dev
	cd frontend && npm install

doctor:
	cd backend && uv run python -m tessera.doctor

# `run` repose sur `trap`/`wait`, sémantiques POSIX : sous Windows, voir
# `run-windows`. Les deux vérifient d'abord les prérequis — les deux pannes de
# ticket-050 étaient détectables avant le lancement.
run: doctor
	@echo "→ Lancement Tessera : backend (port 8000) + frontend (port 5173)"
	@echo "→ Ctrl+C pour arrêter les deux processus"
	@trap 'kill 0' SIGINT SIGTERM; \
	 (cd backend && uv run uvicorn tessera.main:app --reload --host 0.0.0.0 --port 8000 --env-file ../.env) & \
	 (cd frontend && npm run dev) & \
	 wait

dev:
	@echo "→ Serveur démarré sur http://localhost:8000"
	@echo "→ Swagger UI : http://localhost:8000/docs"
	cd backend && uv run uvicorn tessera.main:app \
		--reload \
		--host 0.0.0.0 \
		--port 8000 \
		--env-file ../.env

dev-frontend:
	cd frontend && npm run dev

# Windows : pas de `trap 'kill 0'`, et surtout pas de `--reload`. Tuer le
# parent d'un uvicorn rechargeable laisse son worker vivant, qui garde le port
# 8000 et sert le code de son dernier rechargement — d'où des 500 inexplicables
# et un port impossible à libérer (ticket-056).
run-windows: doctor
	@echo "→ Lancement Tessera sous Windows (deux fenêtres, sans --reload)"
	@powershell -NoProfile -Command "Start-Process -FilePath 'cmd' -ArgumentList '/c','cd backend && uv run uvicorn tessera.main:app --host 127.0.0.1 --port 8000'"
	@powershell -NoProfile -Command "Start-Process -FilePath 'cmd' -ArgumentList '/c','cd frontend && npm run dev'"
	@echo "→ Backend : http://localhost:8000/docs"
	@echo "→ Frontend : http://localhost:5173"
	@echo "→ Pour arrêter : make stop"

stop:
	@echo "→ Arrêt de Tessera"
	-@powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $$_.CommandLine -like '*uvicorn*' } | ForEach-Object { Stop-Process -Id $$_.ProcessId -Force }" 2>/dev/null || true
	-@powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object { $$_.CommandLine -like '*vite*' } | ForEach-Object { Stop-Process -Id $$_.ProcessId -Force }" 2>/dev/null || true
	-@pkill -f 'uvicorn tessera' 2>/dev/null || true
	-@pkill -f 'vite' 2>/dev/null || true
	@echo "→ Arrêté. Vérifie avec make doctor que les ports sont libres."

tauri-dev:
	@echo "→ Lancement de Tessera en mode desktop (Tauri)"
	@echo "→ Assure-toi que 'make dev' tourne dans un autre terminal (FastAPI sur :8000)"
	cd frontend && npm run tauri-dev

tauri-build:
	@echo "→ Build production Tauri"
	cd frontend && npm run tauri-build

verify:
	@echo "→ 1/4 Backend — pytest"
	cd backend && uv run pytest -q -m "not integration"
	@echo "→ 2/4 Backend — mypy"
	cd backend && uv run mypy src/
	@echo "→ 3/4 Frontend — typecheck + vitest"
	cd frontend && npm run typecheck && npm run test -- --run
	@echo "→ 4/4 E2E — playwright"
	cd frontend && npm run test:e2e
	@echo ""
	@echo "Vert. Reste hors de portée ici : cargo check (Rust absent de ce poste)."
	@echo "Il ne tourne en CI que si frontend/src-tauri/ a changé."

test:
	cd backend && uv run pytest -v

test-fast:
	cd backend && uv run pytest -q

test-coverage:
	@echo "→ Backend coverage"
	cd backend && uv run pytest -q -m "not integration" --cov=tessera --cov-report=term-missing --cov-report=html:htmlcov
	@echo "→ Frontend coverage"
	cd frontend && npm run test:coverage

lint:
	cd backend && uv run mypy src/

clean:
	find . -type d -name "__pycache__" -not -path "*/.venv/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -not -path "*/.venv/*" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.mypy_cache
	rm -rf frontend/dist frontend/.vite
