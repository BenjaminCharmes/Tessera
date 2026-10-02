---
id: ticket-319
title: "Agents get their shell on Windows: Tessera finds Git Bash and passes it to the SDK, and says so when it cannot"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-02
---

# ticket-319 — Les agents ont leur shell sous Windows

## Objectif

Que le codeur dispose réellement de l'outil `Bash` qu'on lui déclare, et
qu'une machine où ce n'est pas le cas le dise au démarrage, au lieu de le
laisser découvrir à l'agent.

## Contexte

Constaté le 2026-10-02 sur le ticket-316 : le codeur a écrit « Je n'ai pas
d'outil `Bash` dans cette session », puis a demandé à l'utilisateur de lancer
les tests à sa place. Reproduit hors du pipeline :

- un agent lancé par le SDK avec `tools=["Bash"]` répond qu'il n'a pas de
  shell ;
- le même appel, avec `CLAUDE_CODE_GIT_BASH_PATH` pointé sur
  `…\scoop\apps\git\current\bin\bash.exe`, lance la commande.

Sous Windows, Claude Code n'active `Bash` que s'il trouve Git Bash, et il ne
le cherche qu'aux emplacements standards. Git installé par scoop n'y est pas.
L'outil disparaît alors en silence : aucune erreur, et le prompt continue de
le promettre.

Conséquences observées : le skill `verifier-mon-travail` ne pouvait pas
lancer de tests, le codeur ne vérifiait jamais son travail, et seul le
testeur découvrait les erreurs, un tour plus tard.

## Solution proposée

- Un réglage `git_bash_path`, lu depuis l'environnement
  (`CLAUDE_CODE_GIT_BASH_PATH`) ou, à défaut, déduit sous Windows de
  l'emplacement de `git` (`shutil.which("git")`, puis `…\bin\bash.exe` à côté
  de lui).
- `agent_sdk._build_options` ajoute `CLAUDE_CODE_GIT_BASH_PATH` à l'`env` du
  sous-processus quand le réglage est connu.
- Au démarrage du backend, sous Windows, un Git Bash introuvable produit un
  avertissement explicite dans le journal, et `GET /health` le signale
  (`"agent_shell": false`).

## Critères d'acceptation

- [ ] Un test vérifie que `_build_options` pose `CLAUDE_CODE_GIT_BASH_PATH`
      dans `env` quand `git_bash_path` est connu, et ne le pose pas sinon
- [ ] Un test vérifie que, sous Windows, `git_bash_path` est déduit de
      l'emplacement de `git` quand la variable d'environnement est absente
      (`shutil.which` remplacé par une doublure)
- [ ] Un test vérifie que `GET /health` rend `agent_shell: false` quand aucun
      Git Bash n'est trouvé sous Windows, et `true` sinon
- [ ] Un test vérifie que hors Windows, rien de tout cela ne s'applique et
      `agent_shell` vaut `true`

## Dépendances

Aucune.

## Risques

Donner enfin `Bash` au codeur active pour de bon les garde-fous qui le
visent : le refus du git en écriture (ADR-027) et le périmètre d'écriture
(ADR-031). Ils sont testés, mais n'avaient jamais servi en conditions
réelles sur cette machine.
