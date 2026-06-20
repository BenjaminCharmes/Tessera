---
id: ticket-010
title: "Tauri v2 shell — encapsulation desktop de l'IDE"
type: feat
status: done
priority: medium
agent: codeur
depends_on:
  - ticket-009
created: 2026-06
completed: 2026-06-20
---

# ticket-010 — Tauri v2 Shell ✅

## Ce qui a été fait

### Structure Tauri générée et customisée

```
frontend/src-tauri/
  Cargo.toml            ← nom "vibe-ide", ajout tauri-plugin-fs + tauri-plugin-shell
  tauri.conf.json       ← identifier, fenêtre 1400×900 (min 900×600), CSP pour WS
  src/
    main.rs             ← point d'entrée Rust (appelle vibe_ide_lib::run)
    lib.rs              ← commandes Rust + enregistrement plugins
  capabilities/
    default.json        ← permissions fs + shell ajoutées
```

### Commandes Rust exposées (`src/lib.rs`)

- `read_file(path: String) → Result<String, String>`
- `write_file(path: String, content: String) → Result<(), String>`
- `list_dir(path: String) → Result<Vec<String>, String>`

Plugins enregistrés : `tauri_plugin_fs`, `tauri_plugin_shell`, `tauri_plugin_log`

### Abstraction dual-mode (`frontend/src/lib/fs.ts`)

Détecte `__TAURI_INTERNALS__` pour choisir entre :
- Mode desktop : `invoke()` → commandes Rust
- Mode web/dev : `fetch /api/v1/fs/*` → REST API

### Makefile mis à jour

Nouvelles cibles : `dev-frontend`, `tauri-dev`, `tauri-build`
`setup` installe maintenant aussi les deps npm du frontend.

### CSP configurée

```
connect-src 'self' http://localhost:8000 ws://localhost:8000 https://cdn.jsdelivr.net
```
Monaco CDN (jsdelivr) + FastAPI REST + FastAPI WebSocket autorisés.

## Décision : Option B (backend séparé)

Backend FastAPI lancé manuellement (`make dev`), Tauri se connecte via HTTP/WS.
Option A (sidecar process) en ticket futur.

## Validation

- `cargo check` passe proprement (Finished `dev` profile)
- Compilation Rust : 0 erreur, 0 warning
- Lib name : `vibe_ide_lib` (renommé depuis `app_lib`)
- Permission Tauri corrigée : `fs:allow-mkdir` (pas `fs:allow-create-dir`)

## Pour lancer

```bash
# Terminal 1
make dev          # FastAPI sur :8000

# Terminal 2
make tauri-dev    # Tauri dev window
```
