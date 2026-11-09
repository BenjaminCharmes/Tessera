---
agent: codeur
created: 2026-11-09
depends_on: []
estimated_days: 0.5
id: ticket-891
pr_number: null
priority: high
status: done
title: The editor write route refuses policy files without a declared origin
type: chore
---

# ticket-891 — La route d'écriture de l'éditeur refuse les fichiers de politique sans `Origin` déclaré

## Objectif

Que `PUT /api/v1/fs/write` ne permette pas, à un client qui n'est pas
l'interface, d'écraser les fichiers qui gouvernent les agents (`agents.json`,
`CLAUDE.md`, `.github/workflows/`, `.claude/`) de n'importe quel projet du
workspace.

## Contexte

L'audit externe sans contexte du 06/11 (« Autres failles », gravité haute)
relève que `_is_self_executing` dans `backend/src/tessera/routers/fs.py` ne
refuse que `.git/` et `.claude/settings*.json`. Avec le jeton de session, un
agent peut écrire `CLAUDE.md`, `agents.json` ou un workflow CI par cette route
et contourner le garde de périmètre de son propre processus
(`services/providers/chemins_proteges.py`, ADR-027, ADR-031).

L'éditeur de Tessera est l'outil de l'utilisateur : il doit pouvoir éditer
`CLAUDE.md`. La distinction est celle de l'ADR-075 pour `/api/v1/reglages` :
une écriture sensible exige un `Origin` déclaré, contrôlé dans `auth.py`
(`_is_settings_write`, `_is_declared_origin`). Un agent qui forge l'`Origin`
dans `curl` a été testé le 06/11 sur `PATCH /pipeline` : 401.

## Solution proposée

- Dans `fs.py`, un prédicat `_est_un_fichier_de_politique(resolved)` qui
  réutilise `motif_de_protection` de `chemins_proteges.py` (manifeste, consignes,
  `.github/workflows/`, `.claude/`, hooks du dépôt) : pas de seconde liste.
- `write_file` refuse en 403 un fichier de politique quand la requête n'a pas
  d'`Origin` déclaré, avec le même contrôle que les réglages. Le chemin exact à
  suivre est celui d'`auth.py` ; si le contrôle y est fait par le middleware sur
  une liste de routes, y ajouter `PUT /api/v1/fs/write` pour ces cibles plutôt
  que dupliquer la logique dans le routeur.
- `.git/` et `.claude/settings*.json` restent refusés à tous, comme aujourd'hui.

## Critères d'acceptation

- [ ] `PUT /api/v1/fs/write` sur `agents.json`, `CLAUDE.md`, un fichier sous
      `.github/workflows/` et un fichier sous `.claude/skills/` d'un projet
      répond 403 sans `Origin` déclaré ; un test paramétré couvre les quatre.
- [ ] La même requête avec l'`Origin` de l'interface (`http://localhost:5173`)
      répond 204 et écrit le fichier ; un test le vérifie pour `CLAUDE.md`.
- [ ] Un fichier ordinaire (`src/x.py`) s'écrit sans `Origin` ; un test le
      vérifie.
- [ ] `.git/HEAD` et `.claude/settings.json` répondent 403 même avec l'`Origin`
      de l'interface ; un test le vérifie.
- [ ] Le prédicat des fichiers de politique de `fs.py` appelle
      `motif_de_protection` de `chemins_proteges.py` ; le diff n'ajoute pas de
      liste de noms en double.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Un client légitime autre que Vite (l'app Tauri) doit être dans les origines
déclarées ; vérifier `_declared_origins()` avant de refuser.

## Ce que ça ne fait pas

- Ne ferme pas la lecture du jeton par un agent : c'est l'isolation par compte
  dédié (phase 0 et 1).
- Ne touche pas au dialogue WebSocket partagé (gravité basse, ADR-025).