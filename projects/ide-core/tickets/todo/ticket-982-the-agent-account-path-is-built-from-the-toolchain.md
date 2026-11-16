---
id: ticket-982
preuve_reelle: true
title: "The PATH of every agent-account process is built from the toolchain"
type: fix
status: todo
priority: high
agent: codeur
depends_on: [ticket-981]
---

## Contexte

ADR-086. `lancement_compte.env_du_compte` reprend le `PATH` du backend, qui
mène au profil de l'utilisateur ; `env_agent._de_base` ne donne au CLI que
`System32`, sans la chaîne d'outils.

## Ce qu'il faut faire

- Une fonction unique `path_du_compte()` (dans `services/providers/`, domaine
  le plus bas qui sert les deux appelants) : `toolchain\node`, `toolchain\uv`,
  `toolchain\python` (+ `Scripts`), puis les seules entrées du `PATH` du
  backend qui sont sous `SystemRoot` ou `Program Files` (git). Toute entrée
  sous `C:\Users` est écartée ; une entrée absente du disque aussi.
- `env_du_compte` (tests, app du contrôle visuel) et `env_de_l_agent` (CLI)
  l'utilisent ; `path` quitte `_NOMS_REPRIS`.
- Chaîne absente (`toolchain\node\node.exe` introuvable) : `EchecLancementCompte`
  nommant `agent setup`, jamais de repli sur le `PATH` du backend (ADR-037).

## Critères d'acceptation

- [ ] Test : un `PATH` du backend contenant `C:\Users\x\scoop\shims` donne un
      `PATH` du compte sans aucune entrée sous `C:\Users`.
- [ ] Test : chaîne absente → `EchecLancementCompte`.
- [ ] Un test d'architecture : aucun module ne construit un `PATH` de compte
      hors de `path_du_compte()`.

## Preuve réelle

Faite par la session ide-core après merge et redémarrage, pas par le
validateur : Serpent ticket-009 sous `tessera-agent` passe l'étape de test (`npm run typecheck`).

## Ce que ça ne fait pas

- N'installe rien : ticket-981. Ne règle pas où pointent les venv : ticket-984.
