---
id: ticket-333
title: "A ticket's run strip leaves out queue envelopes and folds runs beyond the three latest"
type: fix
status: done
pr_number: 250
priority: medium
agent: codeur
depends_on: ["ticket-332"]
estimated_days: 0.5
created: 2026-10-05
---

# ticket-333 — La bande des runs d'un ticket écarte les enveloppes de file et se replie

## Objectif

Que la bande « Runs de ce ticket » (ticket-332) ne montre que les vrais runs
du ticket, et reste lisible même après beaucoup de runs.

## Contexte

Retour de l'utilisateur le 2026-10-05, sur le ticket-327 : deux runs
« approuvé » à la même heure. Le second (0 $, 1 tour) est l'enveloppe de la
file 327 → 317 : elle porte l'id du premier ticket de la file et rejoue les
événements de toute la file. `usage_stats` écarte déjà ces enveloppes
(`mode` vaut `queue` ou `autonomous`, ticket-263) ;
`list_runs_for_ticket` (ticket-327) ne le faisait pas.

La bande listait aussi tous les runs terminés : un ticket relancé souvent
repoussait son contenu hors de l'écran.

## Solution proposée

- `list_runs_for_ticket` ne garde que `mode IS NULL OR mode = 'single'`,
  comme `usage_stats`.
- La bande montre les trois derniers runs, puis « Afficher les N autres » ;
  dépliée, sa hauteur est bornée et elle défile.

## Critères d'acceptation

- [x] Un test vérifie que `GET /projects/{id}/tickets/{ticket_id}/runs`
      exclut les runs `queue` et `autonomous` et garde `single` et `NULL`
- [x] Un test rend l'éditeur sur un ticket à huit runs, vérifie que trois
      « Revoir le run » sont visibles, que « Afficher les 5 autres » les
      montre tous, et que « Masquer » revient à trois

## Dépendances

ticket-332.

## Estimation

0,5 jour.
