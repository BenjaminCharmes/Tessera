---
agent: architect
created: 2026-11-12
depends_on: []
estimated_days: 1
id: ticket-944
pr_number: null
priority: high
status: todo
title: "Design: the agent account runs on its own window station and desktop"
type: design
---

# ticket-944 — Conception : le compte agent tourne sur sa propre station et son propre bureau

## Objectif

Choisir comment empêcher un processus du compte agent d'atteindre le bureau
de l'utilisateur (presse-papiers, frappes simulées, captures), puis écrire
les tickets d'implémentation.

## Contexte

Audit du 12/11 (F2). `lanceur_windows.py` laisse `STARTUPINFO.lpDesktop` à
`NULL` : `CreateProcessWithLogonW` donne alors au compte l'accès à
`WinSta0\Default`, le bureau de l'utilisateur. Les deux comptes sont au
niveau d'intégrité medium, donc UIPI ne protège pas : `GetClipboardData`,
`SendInput` vers le terminal au premier plan, hook clavier. Le compte dédié
(ADR-083) n'est donc pas encore la frontière annoncée. Non éprouvé sur la
machine.

## Pistes à comparer

- une window station et un bureau dédiés (`CreateWindowStation`,
  `CreateDesktop`, ACL réservée au compte, `lpDesktop` qui les nomme) ;
- un job avec `JOB_OBJECT_UILIMIT_*` (presse-papiers, handles, atomes
  globaux), combiné au job du ticket-943 ;
- un lancement par tâche planifiée ou service, en session 0.

## Critères d'acceptation

- [ ] Une preuve sur la machine (script hors dépôt, sous
      `~/.tessera/worktrees/manuel/`) : avec le lanceur actuel, un processus
      du compte agent lit-il le presse-papiers de l'utilisateur ?
- [ ] Un ADR dans `memory/decisions.md` retient une piste, avec ses limites
      (Claude CLI, Node et Playwright doivent encore démarrer).
- [ ] Les tickets d'implémentation sont écrits sous `tickets/todo/`.

## Ce que ça ne fait pas

- N'écrit pas de code de production.
