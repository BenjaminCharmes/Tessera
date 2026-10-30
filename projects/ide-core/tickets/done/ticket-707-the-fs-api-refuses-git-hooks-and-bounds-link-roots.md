---
agent: codeur
created: 2026-10-30
depends_on:
- ticket-706
estimated_days: 0.5
id: ticket-707
pr_number: 786
priority: high
status: done
title: The fs API refuses git hooks and CLI settings, and bounds link roots
type: fix
---

# ticket-707 — L'API `fs` refuse les hooks git et les réglages du CLI, et borne les racines de lien (C-05)

## Objectif
L'éditeur de fichiers de l'API ne doit pas écrire ce qui s'exécute tout seul
(hooks git, réglages du CLI). Un import par lien ne doit pas faire d'un dossier
large (racine de disque, dossier personnel) une racine inscriptible.

## Contexte
Audit de sécurité, `docs/audit/securite.md`, constat S-09. `PUT /fs/write`
(`backend/src/tessera/routers/fs.py`, `write_file`) confine les chemins en
résolvant les liens, mais n'applique aucune protection : un
`.git/hooks/pre-commit` peut s'écrire par l'API et s'exécute au commit suivant.
Un projet importé par lien ajoute sa cible à `_workspace_roots`, et
`_validate_source` (`backend/src/tessera/services/project_importer.py`) ne
vérifie que deux choses : que la source existe, et qu'elle ne recouvre pas le
workspace.

Choix fait ici : l'éditeur est l'outil de l'utilisateur. `agents.json`,
`CLAUDE.md` et `.github/workflows/` restent éditables par lui. Seul ce qui
s'**exécute** sans geste de sa part se refuse : `.git/` et
`.claude/settings*.json`.

## Solution proposée
- `write_file` refuse en 403 tout chemin dont un segment est `.git`, ou qui
  vise un `.claude/settings*.json`.
- `_validate_source` refuse une source qui est une racine de disque, le dossier
  personnel de l'utilisateur (`Path.home()`) ou l'un de ses parents.

## Critères d'acceptation
- [ ] `test_fs_write_to_git_hooks_is_refused` (dans `backend/tests/test_fs_router.py`) : `PUT /api/v1/fs/write` vers `<projet>/.git/hooks/pre-commit` → 403, et le fichier n'est pas créé
- [ ] `test_fs_write_to_claude_settings_is_refused` : vers `<projet>/.claude/settings.local.json` → 403
- [ ] `test_fs_write_to_agents_json_still_passes` : vers `<projet>/agents.json` → succès
- [ ] `test_read_of_a_protected_file_is_still_allowed` : `GET /api/v1/fs/read` de `<projet>/.git/HEAD` réussit
- [ ] `test_symlink_import_of_home_or_drive_root_is_refused` (dans `backend/tests/test_project_importer.py`) : une source égale à `Path.home()`, à l'un de ses parents ou à une racine de disque lève `ImportError`

## Ce que ça ne fait pas
- Ne restreint pas la lecture
- Ne remplace ni `STATIC_TOKEN` ni ticket-704, qui ferment l'accès distant