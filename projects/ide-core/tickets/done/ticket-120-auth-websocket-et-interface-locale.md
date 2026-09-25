---
id: ticket-120
title: "Protéger les WebSockets par STATIC_TOKEN et servir en local par défaut"
type: fix
status: done
pr_number: 139
priority: critical
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-22
---

# ticket-120 — Protéger les WebSockets par STATIC_TOKEN et servir en local par défaut

## Objectif

Que `STATIC_TOKEN`, une fois renseigné, protège **toutes** les routes comme
`config.py` et `CLAUDE.md` le promettent, et que l'API ouverte par défaut ne
soit servie que sur l'interface locale.

## Contexte

- `StaticTokenMiddleware` hérite de `BaseHTTPMiddleware`, dont `__call__`
  laisse passer tout scope non-`http` sans appeler `dispatch`. Les trois routes
  `@router.websocket` (pipeline, chat, agents stream) restent ouvertes.
- La comparaison `auth != f"Bearer {token}"` n'est pas en temps constant.
- Le middleware est ajouté après CORS, donc le plus externe : un préflight
  `OPTIONS` sans `Authorization` reçoit 401.
- Le frontend n'envoie jamais de Bearer : renseigner le token = UI en 401.
- `Makefile` (`dev`, `run`) et `src-tauri/src/lib.rs` lancent uvicorn sur
  `0.0.0.0` ; seule la cible Windows est sur `127.0.0.1`.
- `.env.example` ne mentionne pas `STATIC_TOKEN` ni cinq autres variables
  lues par `config.py`.

## Solution proposée

1. Remplacer le middleware par un middleware ASGI pur qui traite
   `scope["type"] in ("http", "websocket")`, lit `scope["headers"]`, laisse
   passer `OPTIONS` et `/health`, compare avec `hmac.compare_digest`. Pour les
   WebSockets, accepter aussi `?token=` (les navigateurs ne posent pas d'en-tête
   sur `new WebSocket`) et fermer avec le code 4401 sinon.
2. Frontend : `lib/api.ts`, `lib/ws.ts`, `lib/fs.ts` lisent
   `import.meta.env.VITE_STATIC_TOKEN` et ajoutent `Authorization` / `?token=`
   quand il est défini. Documenter dans `docs/configuration.md`.
3. `--host 127.0.0.1` dans `Makefile` (`dev`, `run`). Le fichier
   `src-tauri/src/lib.rs` est traité par ticket-124 : ne pas le toucher ici.
4. `.env.example` complété avec `STATIC_TOKEN`, `RUN_MAX_BUDGET_USD`,
   `CHAT_MAX_CONVERSATION_USD`, `GITHUB_BASE_BRANCH`, `DIALOGUE_TIMEOUT_S`,
   `IDE_DB_PATH`, valeurs par défaut et une ligne d'explication chacune.

Hors périmètre : comptes utilisateurs, rotation de token, shell Tauri.

## Critères d'acceptation

- [ ] Test : avec `STATIC_TOKEN` renseigné, une connexion WebSocket sans token
      est refusée, avec `?token=` correct elle est acceptée
- [ ] Test : `GET /api/v1/projects` sans Bearer → 401, avec → 200, `OPTIONS`
      sans Bearer → pas de 401, `/health` toujours 200
- [ ] Test frontend : `api.get` pose `Authorization` quand `VITE_STATIC_TOKEN`
      est défini, ne le pose pas sinon ; `ws.ts` ajoute `?token=`
- [ ] `grep -n "0.0.0.0" Makefile` ne renvoie rien
- [ ] `.env.example` mentionne chaque variable de `config.py`
      (`docs/configuration.md` en fait la liste)
- [ ] `uv run pytest -q`, `uv run mypy src/`, `npm run typecheck`,
      `npm run test` verts

## Dépendances
Aucune.

## Estimation
1 jour.

## Risques
Le `?token=` part dans les logs d'accès uvicorn : à noter dans la doc.

## Ce que ça ne fait pas

- **Pas de comptes, pas de rotation** : un seul secret partagé entre le poste
  et son backend. `VITE_STATIC_TOKEN` est inliné dans le bundle Vite — quiconque
  a le build a le token. C'est le modèle voulu pour un outil local.
- **Le `?token=` WebSocket reste en clair dans les logs d'accès** uvicorn et
  dans tout proxy. Un navigateur ne peut pas poser d'en-tête sur
  `new WebSocket` ; l'alternative (sous-protocole, premier message) aurait
  demandé de toucher les trois routes et les hooks, hors périmètre.
- **`src-tauri/src/lib.rs` lance toujours uvicorn sur `0.0.0.0`** : c'est
  ticket-124. Le shell Tauri n'envoie pas non plus le token — même ticket.
- **`/health` reste ouvert** : la sonde n'expose que la version.
- **Une WebSocket refusée reçoit `4401` sans corps** : les hooks n'affichent
  pas encore de message dédié, ils voient une fermeture (ticket-123).
- **Le mode Tauri de `fs.ts`** passe par `invoke`, pas par HTTP : le token ne
  le concerne pas.
