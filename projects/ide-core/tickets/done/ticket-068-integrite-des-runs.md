---
id: ticket-068
title: "Intégrité d'un run — l'agent ne fait pas de git, et un run ne ment pas sur son résultat"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: [ticket-066]
estimated_days: 2
created: 2026-09-17
---

# ticket-068 — Intégrité d'un run

## Ce qui s'est passé

Premier usage réel, 2026-09-17, projet `tmp`. Deux tickets lancés depuis l'UI,
aucune autre action de l'utilisateur. Constaté dans le dépôt :

- trois commits écrits par les agents, avec **leurs propres messages**, portant
  du travail **hors périmètre des tickets** (module « time warp »,
  `holdForFourLeaf`, `timewarpOff`, `PROGRESS.md` réécrit)
- la branche de ticket **mergée dans `main`** en fast-forward
- `main` **poussée sur GitHub** (`origin/main` = `cdbd9c3`, zéro commit local)
- aucun commit au format d'ADR-018 (`feat: ticket-001 — …`)
- les deux tickets affichés `done`

## Pourquoi

**Le codeur a `Bash`.** `GitWorkspaceService` n'est qu'une des façons de faire
du git : l'agent lance `git commit`, `git merge`, `git push` directement. Tout
ce qu'ADR-018 et ADR-022 garantissent ne contraint qu'une classe que l'agent
n'est pas obligé d'utiliser. ADR-022 dit « l'agent ne merge jamais » — rien ne
l'en empêchait.

Et quand le pipeline, lui, ne parvient pas à committer, l'échec est avalé :
`commit_failed` part en `warning` et le run annonce quand même APPROVED.

## Décision

1. **Aucun agent ne fait de git qui modifie l'historique.** Refus au niveau du
   SDK (`can_use_tool`), pas dans le prompt : une consigne n'est pas une
   garantie. Le git en lecture reste permis.
2. **Un run qui devait committer et n'a pas commité ne peut pas se dire
   approuvé.** « Rien à committer » et « le commit a échoué » sont deux états
   distincts, et le second est bruyant.
3. **La raison d'un refus arrive à l'écran.** Le backend envoyait
   `reason="dirty_working_tree"`, le frontend lisait `message` → « Erreur:
   unknown ».
4. **Une reconnexion WebSocket ne relance pas un run.** Elle en a lancé trois.

## Critères d'acceptation

- [x] `git commit`, `merge`, `push`, `checkout`, `switch`, `branch`, `reset`,
      `rebase`, `cherry-pick`, `tag`, `stash` et `add` sont refusés à l'agent
- [x] `git status`, `diff`, `log`, `show` restent permis
- [x] Le refus porte un message qui dit à l'agent que committer est le travail
      du pipeline, pas le sien
- [x] Les formes détournées sont couvertes : `cd x && git push`, `git -C path
      commit`, espaces multiples
- [x] Un échec de commit fait échouer le run, avec la raison
- [x] « Rien à committer » reste un succès, et se distingue à l'écran
- [x] Le log de l'UI affiche la raison réelle d'un refus
- [x] Une reconnexion ne redémarre pas le pipeline
- [x] `npm run typecheck`, tests unitaires, E2E et `npm run build` verts

## Hors scope

- Le bouton stop (ticket suivant)
- L'affichage du diff
