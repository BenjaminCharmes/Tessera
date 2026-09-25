---
id: ticket-124
title: "Rendre l'app Tauri packagée fonctionnelle sans réouvrir le filesystem"
type: fix
status: done
pr_number: 142
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-22
---

# ticket-124 — Rendre l'app Tauri packagée fonctionnelle sans réouvrir le filesystem

## Objectif

Qu'un `tauri build` produise une app qui joint son backend, et que le shell
desktop n'offre pas plus d'accès disque que l'API.

## Contexte

- `lib/api.ts` (`BASE = "/api/v1"`), `lib/ws.ts` (`location.host`), `lib/fs.ts`
  utilisent des URL relatives. En dev le proxy Vite les résout ; en release
  (`tauri://localhost`) rien ne sert l'API. Le CSP autorise
  `http://localhost:8000` mais rien ne l'utilise.
- `src-tauri/src/lib.rs` : `read_file` / `write_file` / `list_dir` sans aucun
  contrôle de chemin, alors que `routers/fs.py` refuse tout chemin hors
  workspace (écrit après le trou `?path=~/.ssh/id_rsa`). `lib/fs.ts` les
  préfère dès que `__TAURI_INTERNALS__` existe. Les permissions `fs:*` de
  `capabilities/default.json` sont inertes : `@tauri-apps/plugin-fs` n'est pas
  une dépendance.
- `spawn_backend` lance `sh -c …` (absent sous Windows) avec `--host 0.0.0.0`,
  depuis un `BACKEND_DIR` résolu à la compilation.
- CSP `script-src 'unsafe-inline' 'unsafe-eval'` : Monaco bundlé n'a pas
  besoin d'`unsafe-eval`.

## Solution proposée

1. `lib/config.ts` : `API_ORIGIN = import.meta.env.VITE_API_URL ?? ""` ; `api`,
   `ws`, `fs` s'en servent. Un `.env.production` dans `frontend/` pose
   `VITE_API_URL=http://127.0.0.1:8000`. Documenter dans
   `docs/configuration.md`.
2. Supprimer les trois commandes Rust et la branche Tauri de `lib/fs.ts` : le
   backend est la seule porte vers le disque. Retirer `fs:*` et
   `shell:allow-open` de `capabilities/default.json`.
3. `spawn_backend` : `Command::new("uv")` avec arguments listés, sans shell,
   `--host 127.0.0.1` ; `BACKEND_DIR` lu depuis une variable d'environnement
   `TESSERA_BACKEND_DIR` avec repli sur la valeur compilée ; log si le spawn
   échoue.
4. CSP sans `'unsafe-eval'`.

Hors périmètre : packaging du backend Python dans le bundle, auto-update,
en-tête d'authentification (ticket-120), hooks React (ticket-123).

## Critères d'acceptation

- [x] Test : avec `VITE_API_URL=http://x:1`, `api.get("/projects")` appelle
      `http://x:1/api/v1/projects` et `ws.ts` ouvre `ws://x:1/…`
- [x] `grep -n "read_file\|write_file\|list_dir" frontend/src-tauri/src/lib.rs`
      ne renvoie rien ; `grep -rn "__TAURI_INTERNALS__" frontend/src` non plus
- [x] `capabilities/default.json` ne contient plus `fs:` ni `shell:`
- [x] `grep -n "0.0.0.0\|\"sh\"" frontend/src-tauri/src/lib.rs` ne renvoie rien
- [x] `tauri.conf.json` : CSP sans `unsafe-eval`
- [ ] `npm run typecheck`, `npm run test`, `npm run build` verts ;
      `cargo check` vert en CI (job Tauri déclenché par le diff Rust)

## Ce que ça ne fait pas

- Le backend Python n'est **pas** embarqué dans le bundle : l'app release
  suppose `uv` installé et un dossier `backend/` désigné par
  `TESSERA_BACKEND_DIR` (repli sur le chemin compilé).
- Un spawn raté est écrit sur stderr, que Windows n'affiche pas en release
  (`windows_subsystem = "windows"`) : l'app s'ouvre alors sur une erreur
  réseau, pas sur un message.
- `cargo check` n'a pas tourné en local — `cargo` n'est pas installé. La
  vérification Rust repose sur le job Tauri de la CI ; `Cargo.lock` a été
  élagué à la main des deux plugins retirés.
- `@tauri-apps/api` reste dans `package.json` bien que plus rien ne l'importe :
  le retirer demande un `npm install` qui réécrit le lockfile, hors de ce
  ticket.
- Pas d'en-tête d'authentification (ticket-120), pas de changement dans les
  hooks ou composants (ticket-123).

## Dépendances
Aucune.

## Estimation
1 jour.

## Risques
`cargo` n'est pas installé sur le poste de développement : la vérification
Rust repose sur la CI.
