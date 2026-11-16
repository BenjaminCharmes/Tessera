---
id: ticket-981
preuve_reelle: true
title: "agent setup installs a shared toolchain outside every profile"
type: fix
status: todo
priority: high
agent: codeur
depends_on: []
---

## Contexte

ADR-086. Le compte `tessera-agent` n'a aucun droit sur le profil de
l'utilisateur ; node, uv et Python y vivent (scoop, `%APPDATA%\uv`,
`~\.local\bin`). Serpent ticket-009 échoue : `EPERM … lstat '…\scoop'`.

## Ce qu'il faut faire

- `scripts/agent-setup-admin.ps1` crée `C:\ProgramData\Tessera\toolchain\` :
  `SYSTEM` et Administrateurs en contrôle total, le propriétaire (utilisateur)
  en modification, `tessera-agent` en lecture-exécution seule, héritage coupé
  (par SID, comme le dossier des worktrees).
- `scripts/agent-setup.ps1` (sans admin) y copie, sous `node\`, `uv\` et
  `python\` : le dossier de la version courante de node (le vrai dossier, pas
  la jonction `current` de scoop), `uv.exe`/`uvx.exe`, et un Python obtenu par
  `uv python install` avec `UV_PYTHON_INSTALL_DIR=…\toolchain\python`.
  Idempotent : une copie déjà à la bonne version est laissée.
- Retire les droits `RX` que `Copy-AgentCli` donne sur `scoop\apps`,
  `AppData\Roaming\uv\python` et `.local\bin` (`icacls /remove`), puis ne les
  redonne plus.

## Critères d'acceptation

- [ ] Après `agent setup`, `toolchain\node\node.exe`, `uv\uv.exe` et un Python
      existent, et le compte agent n'y écrit pas.
- [ ] Plus aucun droit de `tessera-agent` sur le profil de l'utilisateur
      (`icacls` ne liste plus le compte).
- [ ] Relancer `agent setup` ne recopie rien quand les versions sont égales.

## Preuve réelle

Faite par la session ide-core après merge et redémarrage, pas par le
validateur : Serpent ticket-009 sous `tessera-agent` passe l'étape de test (avec ticket-982).

## Ce que ça ne fait pas

- Ne change pas le `PATH` du compte : ticket-982.
- Ne touche pas aux droits du dossier des worktrees : ticket-975.
