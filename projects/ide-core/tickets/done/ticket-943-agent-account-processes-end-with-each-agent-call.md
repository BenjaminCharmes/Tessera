---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 2
id: ticket-943
pr_number: null
preuve_reelle: true
priority: high
status: done
title: Processes of the agent account end with each agent call, and the worktree right
  is withdrawn between calls
type: fix
---

# ticket-943 — Les processus du compte agent finissent avec chaque appel, et le droit d'écriture est retiré entre deux appels

## Objectif

Qu'aucun processus lancé sous `AGENT_USER` ne survive à l'appel qui l'a lancé,
et que le compte agent ne puisse écrire dans un worktree que pendant un appel
d'agent, une commande de test ou l'app du contrôle visuel.

## Contexte

Audit du 12/11 (F1). Sous `AGENT_USER`, `lanceur_windows.py` crée le CLI par
`CreateProcessWithLogonW` sans `CREATE_SUSPENDED` ni job. Le rattachement à
un job passe par `OpenProcess` sur un processus d'un autre compte
(`agent_non_rattache`), et `lancement_compte.py` le reconnaît : « Le lanceur
Windows ne crée pas de job ». `droits_worktree.py` accorde `M` au compte sur
tout le worktree et ne le retire jamais.

Un processus laissé en fond par l'agent peut donc modifier l'arbre après la
revue, avant le `git add -A` de fin de run : du code non relu part dans le
commit approuvé. Il peut aussi écrire plus tard dans le worktree d'un autre
projet, dont le chemin est prévisible.

## Solution proposée

1. Lancement avec `CREATE_SUSPENDED`, affectation du `hProcess` rendu par
   `CreateProcessWithLogonW` à un job `KILL_ON_JOB_CLOSE`, puis
   `ResumeThread`. Même chose pour `lancer_sous_compte` (tests, app).
2. À la fin de chaque appel et de chaque commande sous compte : fermeture du
   job, arrêt de tout processus restant dont le propriétaire est
   `AGENT_USER` (journalisé avec son nom d'image), puis retrait de l'ACE du
   compte sur le worktree (`icacls /remove`). Le droit est reposé au
   lancement suivant.
3. Si le retrait ou l'arrêt échoue, le run passe en `blocked` (ADR-037).

## Preuve réelle

Sur serpent (`worktree.compte_agent`), lancer un run réel sous `tessera-agent`,
puis, après chaque appel d'agent :
- `Get-CimInstance Win32_Process` filtré sur le propriétaire `tessera-agent` :
  aucun processus restant ;
- `icacls <worktree du run>` : plus d'ACE `tessera-agent` entre deux appels,
  de nouveau présente pendant un appel ;
- le run finit `done` ou `blocked` avec son commit, jamais un arbre sale.

## Critères d'acceptation

- [ ] Un test, avec un lanceur double : le lanceur demande
      `CREATE_SUSPENDED`, affecte le processus à un job, puis le reprend.
- [ ] Un test : après un appel sous compte, le retrait des droits est
      appelé sur le worktree, et leur pose avant l'appel suivant.
- [ ] Un test : un échec du retrait met le run en `blocked`.
- [ ] Un test : les processus restants du compte sont arrêtés à la fin de
      l'appel (double de l'énumération).

## Ce que ça ne fait pas

- Ne fait pas relire un SHA plutôt que l'arbre : avec ce ticket, plus rien
  ne peut écrire entre la revue et le commit de fin de run.
- Ne sépare pas le bureau du compte agent : ticket-944.