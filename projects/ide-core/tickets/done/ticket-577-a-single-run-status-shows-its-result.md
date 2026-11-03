---
agent: codeur
created: 2026-10-26
depends_on: []
estimated_days: 0.25
id: ticket-577
pr_number: 691
priority: medium
status: done
title: The status of a single-ticket run shows its ticket as approved or stopped
type: fix
---

# ticket-577 — Le statut d'un run d'un seul ticket dit son issue

## Objectif
Que `GET /api/v1/runs/{id}` d'un run lancé en mode `single` dise si son ticket
a été approuvé, comme pour une file.

## Contexte
Signalé par la session Kadoomi le 26/10 : le run `d933ebfb…` (ticket-112,
mode `single`) a des événements `pipeline_done` approved=true, PR #164,
`ci_merge_done` merged=true, `run_closed` final_status=done ; pourtant le
statut renvoie `statut="terminé"`, `approuves=[]`, `arretes=[]`, `faits=[]`.
Un outil qui juge le run sur ce statut le croit sans résultat (le 24/10, un
script d'enchaînement s'est arrêté pour cette raison). Les fuseaux diffèrent
aussi : `debut` est rendu en UTC une fois le run fini, en +01:00 pendant le
run.

Le statut d'un run fini vient de `statut_en_base`
(`services/run_status.py`), celui d'un run vivant de
`statut_d_un_run_vivant`.

## Critères d'acceptation
- [ ] Un test montre que `statut_en_base` d'un run `single` approuvé rend son ticket dans `approuves` et dans `faits`
- [ ] Un test montre que `statut_en_base` d'un run `single` non approuvé rend son ticket dans `arretes`
- [ ] Un test montre que `debut` est rendu dans le même fuseau par `statut_d_un_run_vivant` et par `statut_en_base`
- [ ] Les tests existants du statut d'une file restent inchangés dans le diff