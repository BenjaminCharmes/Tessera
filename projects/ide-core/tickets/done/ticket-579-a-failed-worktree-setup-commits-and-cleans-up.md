---
agent: codeur
created: 2026-10-26
depends_on: []
estimated_days: 0.5
id: ticket-579
plan: true
pr_number: null
priority: high
status: done
title: A run whose worktree setup fails commits its bookkeeping and removes its worktree
type: fix
---

# ticket-579 — Une préparation de worktree en échec range derrière elle

## Objectif
Qu'un run arrêté par l'échec de la préparation de son worktree laisse un
arbre propre et un worktree retiré, comme tout autre run bloqué.

## Contexte
Signalé par la session Kadoomi le 26/10 : run `c14c794b…` (ticket-113, mode
single). La commande de préparation (`corepack pnpm@10 install
--frozen-lockfile`, ticket-536) a été coupée au bout de 420 s, la machine
étant chargée par d'autres files. Le run s'est fermé en `blocked` avec
rounds=0, sans branche ni commit, et le worktree est resté en place avec du
travail non commité : `memory/pipeline-log.md` modifié, le ticket déplacé de
`todo/` vers `blocked/`. C'est contraire à l'ADR-037 (toute exception termine
le run en `blocked` **avec commit**) et à l'ADR-056. Tant que le dossier
existe, le ticket ne peut pas être relancé : il a fallu le ranger à la main.

L'échec vient de `preparer_le_worktree` (`services/preparation_worktree.py`),
appelé par `services/run_dans_worktree.py` avant tout agent.

## Solution proposée
Sur un échec de préparation : commiter le rangement sur la branche du run
(`chore: … — unapproved work (worktree setup failed: …)`), puis retirer le
worktree par `supprimer` (`services/run_worktree.py`), qui vide aussi ce que
git laisse (chemins longs, ticket-551). Le tour de plan dit aussi si le délai
de la préparation doit être distinct de celui des tests.

## Critères d'acceptation
- [ ] Un test, avec une préparation qui échoue, montre que le run se ferme `blocked` avec un commit « unapproved work » sur sa branche
- [ ] Le même test montre que le worktree du run n'existe plus après la fermeture
- [ ] Un test montre que le ticket peut être relancé après un tel échec (le worktree se recrée au même chemin)
- [ ] La ligne de `memory/pipeline-log.md` de l'échec nomme la commande et la durée