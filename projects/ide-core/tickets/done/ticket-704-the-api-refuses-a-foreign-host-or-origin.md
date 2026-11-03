---
agent: codeur
created: 2026-10-30
depends_on: []
estimated_days: 1
id: ticket-704
pr_number: 777
priority: critical
status: done
title: The API refuses a foreign Host or Origin
type: fix
---

# ticket-704 — L'API refuse un `Host` ou un `Origin` étranger (C-02)

## Objectif
Même avec `STATIC_TOKEN` vide, une page web visitée par l'utilisateur ne doit
ni lire les runs par WebSocket, ni piloter l'API par rebond DNS.

## Contexte
Audit de sécurité, `docs/audit/securite.md`, constat S-02 (CRITICAL). Avec
`STATIC_TOKEN` vide, tout passe (`backend/src/tessera/auth.py`). Le CORS de
`backend/src/tessera/main.py` n'empêche qu'une chose : qu'une page tierce
*lise* une réponse. Il ne s'applique pas aux WebSocket. Aucun contrôle ne porte
sur `Host` : par rebond DNS, une page tierce peut appeler
`PATCH /projects/{id}/pipeline` pour fixer `test_command`, puis
`POST /orchestrator/run`.

Les clients légitimes :
- le Vite de dev (`http://localhost:5173`) et les Vite de worktree, sur
  d'autres ports locaux (5174, 5175) ; leur proxy (`frontend/vite.config.ts`,
  `changeOrigin: true`) transmet l'en-tête `Origin` du navigateur ;
- l'app Tauri (`tauri://localhost`, `http://tauri.localhost`,
  `https://tauri.localhost`) ;
- les outils et les tests, qui n'envoient pas d'`Origin`.

## Solution proposée
Un middleware ASGI pur, à côté de `StaticTokenMiddleware` dans `auth.py`. Même
raison que pour lui : `BaseHTTPMiddleware` ne voit pas les WebSocket.
- `Host`, port retiré, doit être `127.0.0.1`, `localhost`, `[::1]`, ou un nom
  du nouveau réglage `allowed_hosts` (`ALLOWED_HOSTS`, vide par défaut : le
  loopback seul). Sinon : 403 en HTTP, fermeture en WebSocket.
- Un `Origin` présent doit être une origine loopback (`http://localhost:<port>`
  ou `http://127.0.0.1:<port>`, tout port) ou une origine Tauri listée
  ci-dessus. Sinon : 403 en HTTP, fermeture en code 4403 en WebSocket.
- Sans `Origin`, la requête passe (outils, curl, tests).
- `/health` reste ouvert.

`docs/configuration.md` documente le réglage.

## Critères d'acceptation
- [ ] `test_foreign_host_is_refused` : `Host: evil.example` sur `GET /api/v1/projects` → 403, avec `STATIC_TOKEN` vide
- [ ] `test_declared_host_passes` : un nom listé dans `allowed_hosts` passe
- [ ] `test_foreign_origin_http_is_refused` : `Origin: https://evil.example` sur une route HTTP → 403
- [ ] `test_foreign_origin_websocket_is_closed` : un handshake WebSocket sur `/api/v1/orchestrator/observe` avec `Origin: https://evil.example` est fermé en code 4403
- [ ] `test_listed_origin_and_missing_origin_pass` : `http://localhost:5173`, `http://localhost:5175`, `http://tauri.localhost` et une requête sans `Origin` passent
- [ ] `test_health_stays_open` : `GET /health` avec un `Host` étranger renvoie 200
- [ ] `docs/configuration.md` décrit `ALLOWED_HOSTS`

## Ce que ça ne fait pas
- N'ajoute ni comptes ni authentification (hors scope)
- Ne protège pas contre un processus local : le loopback reste de confiance

## Risques
Bloquer le vrai frontend. Le cinquième critère couvre les origines du Vite de
dev et de Tauri.