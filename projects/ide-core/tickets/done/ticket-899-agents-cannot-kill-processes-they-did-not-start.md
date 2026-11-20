---
agent: codeur
created: 2026-11-09
depends_on: []
estimated_days: 1
id: ticket-899
pr_number: 1000
priority: high
status: done
title: Agents cannot kill processes by name, nor by a PID they did not start
type: fix
---

# ticket-899 — Un agent ne tue pas les processus de la machine

## Objectif

Refuser à un agent, au même hook `PreToolUse` que le git en écriture, toute
commande `Bash` qui tue des processus par leur nom ou par un PID qu'il n'a pas
lancé lui-même dans la même commande.

## Contexte

Le 2026-11-09 à 15:09 UTC, le codeur du run Kadoomi `eeac187c` (ticket-145) a
lancé `pkill -f "python" 2>/dev/null; true` en queue d'un `grep`. La commande
vise tous les processus Python de la machine : le backend Tessera, les services
des projets, les hooks eux-mêmes. L'agent est resté muet ensuite, puis le run a
été coupé au bout de 1 200 s (`ProviderIndisponible`), et rien n'a été livré.
Aucun dégât cette fois-ci, parce que les services d'Affût et de Vigie étaient
déjà arrêtés.

`hook_refus_git` (`backend/src/tessera/services/providers/git_guard.py`) lit
déjà chaque segment d'une ligne de shell. Il déballe ses enveloppes (`env`,
`sudo`, `sh -c`, `eval`…) avec `git_guard_lexique.py`. Les commandes qui
tuent n'y passent pas.

L'isolation par compte dédié (tickets 894 à 896) empêchera à terme un agent de
toucher aux processus de l'utilisateur. Elle ne couvre pas encore ide-core ni
les projets sans worktree. Ce garde attrape une erreur, pas une évasion
(ADR-031).

## Solution proposée

- Un module `kill_guard.py` dans `services/providers/`. Il réutilise
  `git_guard_lexique` (segments, jetons, enveloppes, shells) et refuse un
  segment dont la commande est :
  - `pkill`, `killall`, `taskkill`, `tskill`, `Stop-Process`, `spps` ;
  - `wmic … process … delete` / `call terminate` ;
  - `kill` avec un PID numérique, `-1`, `0`, ou un argument `$(…)` /
    backticks.
- Reste permis : `kill %1` (job du shell), `kill $!` (dernier processus lancé
  par cette même ligne), `timeout …`.
- Refusé aussi derrière `sh -c`, `bash -c`, `cmd /c`, `powershell -Command`,
  `pwsh -c`, `eval`, `xargs`, comme pour git.
- Le hook est branché dans `agent_sdk.py` à côté de `hook_refus_git`, sur
  `Bash`. Le message de refus explique à l'agent que les processus lancés par
  les tests sont arrêtés par le pipeline, et qu'il doit lancer en arrière-plan
  et arrêter avec `kill $!`.

## Critères d'acceptation

- [ ] `kill_guard.py` existe dans `backend/src/tessera/services/providers/`
      et expose une fonction `commande_kill_interdite(commande: str) -> bool`
- [ ] Un test vérifie que `commande_kill_interdite` renvoie `True` pour
      `grep -r x . ; pkill -f "python" 2>/dev/null; true`, `killall node`,
      `taskkill /F /IM python.exe`, `Stop-Process -Name python`,
      `kill -9 1234`, `kill -1`, `kill $(pgrep python)`,
      `sh -c "pkill python"` et `powershell -Command "Stop-Process -Name node"`
- [ ] Un test vérifie que `commande_kill_interdite` renvoie `False` pour
      `kill %1`, `npm run dev & sleep 5; kill $!`, `grep pkill notes.md` et
      `echo killall`
- [ ] `agent_sdk.py` enregistre le hook de `kill_guard.py` sur le matcher
      `Bash`, et un test vérifie qu'il renvoie `permissionDecision: "deny"`
      pour `pkill -f python` et `{}` pour `ls`
- [ ] Le message de refus mentionne `kill $!`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

- Un faux positif empêcherait un agent d'arrêter le serveur qu'il a lancé pour
  un test. `kill $!` et `kill %N` restent ouverts pour ça.
- Ce garde n'est pas une frontière de sécurité : `python -c "import os; …"`
  passe. La frontière, c'est l'isolation par compte (894-896).