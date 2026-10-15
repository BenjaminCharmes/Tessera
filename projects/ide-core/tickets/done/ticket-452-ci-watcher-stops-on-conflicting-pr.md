---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 0.5
id: ticket-452
plan: true
pr_number: null
priority: high
status: done
title: The CI watcher stops with a message when a watched PR is in conflict
type: fix
---

# ticket-452 — Une PR en conflit ne reste pas muette dans le CIWatcher

## Objectif

Une PR surveillée par le CIWatcher qui devient non fusionnable produit une
ligne d'arrêt dans `pipeline-log.md`, débloque les tickets qui l'attendent
en échec, et ne reste pas en attente sans le dire.

## Contexte

make-your-call, 15/10 : la PR #14 (ticket-002), confiée au CIWatcher à
10:20, CI verte, est passée CONFLICTING après le merge d'une autre PR. Une
demi-heure plus tard : aucune ligne d'arrêt, rien de visible, la file a
continué (005, 006, 007).

`backend/src/tessera/services/ci_watcher.py` lance `livrer_phase_2`
(attente de CI puis `merge_quand_fusionnable` dans
`backend/src/tessera/services/github_service.py`, qui lève
`PRNonFusionnableError`). Le plan doit établir où la PR est restée : attente
de CI, attente de fusionnabilité (`mergeable` null), sémaphore du projet
occupé par une autre surveillance, ou exception avalée.

## Solution proposée

- Lire `mergeable` / `mergeable_state` pendant l'attente de CI : une PR
  `dirty` arrête la surveillance aussitôt, avec « PR #N en conflit avec
  <base> : à rebaser ».
- L'échec est enregistré comme un non-merge : les dépendants qui attendent
  ce ticket le reçoivent en échec (file interrompue, ADR-051).

## Critères d'acceptation

- [ ] Un test vérifie qu'une PR dont `mergeable_state` vaut `dirty`
      pendant l'attente de CI arrête la surveillance sans attendre le délai
- [ ] Un test vérifie que cet arrêt écrit une ligne dans `pipeline-log.md`
      qui contient le numéro de la PR et le mot « conflit »
- [ ] Un test vérifie qu'`attendre_merge` rend alors `False`
- [x] Le lieu où la PR #14 est restée bloquée est décrit dans la PR : elle
      n'a jamais été dans le CIWatcher. Un conflit résolu par
      `resolveur-conflit` ne confie pas sa PR au watcher (ADR-033), et la
      ligne « confiée au CIWatcher » est écrite quand même. Détail, avec les
      lignes de journal, dans la section « Diagnostic de la PR #14 »

## Diagnostic de la PR #14

Le plan avançait trois pistes (redémarrage, sémaphore, boucle de CI). Aucune
n'est la bonne : la PR n'a **jamais été surveillée**. Preuves, dans l'ordre :

1. `backend/logs/tessera.log`, 15/10 (UTC) : `10:20:22 resolution_de_conflit`
   sur `docs/guide-utilisateur.md` et `memory/documentation.json`, puis
   `10:20:48 pull_request_opened` (PR #14). Le rebase de livraison avait donc
   rencontré un conflit, que `resolveur-conflit` a tranché.
2. `LivraisonService._apres_ouverture` (`livraison.py`) rend alors une
   livraison dont l'`arret` est « Conflit résolu … la PR #14 est ouverte, à
   relire. Une résolution de conflit ne se merge jamais toute seule »
   (ADR-033). `Orchestrator` n'appelle `surveiller` que si `arret is None`
   ou si la PR est orpheline (`orchestrator.py`, l. 261-266) : ici, jamais.
3. Aucune ligne `ci_merge_done`, `ci_merge_blocked`, `ci_watcher_*` ni
   `merge_effectue` ne porte `"pr": 14` dans tout le journal du jour, alors
   que les PR #13, #15, #16 et #17 du même projet en ont chacune une. Le
   watcher n'a donc rien eu à dire : il n'a jamais reçu cette PR.
4. La ligne `10:20:56 ticket-002 PR #14 confiée au CIWatcher` est écrite par
   la boucle de file (`orchestrator.py`, l. 675-678) dès que la livraison a un
   `pr_number`, qu'un watcher ait été lancé ou non. Elle est fausse ici.
5. Juste avant, `_attendre_si_dependant` a appelé `attendre_merge` pour
   ticket-002, que ticket-003 attend. Ticket-002 n'étant pas inscrit,
   `attendre_merge` a rendu `True` par défaut (« jamais inscrit »). D'où
   `10:20:56 base réalignée sur main`, qui n'est écrite que sur ce `True`,
   puis `10:21:01 ticket-003 codeur démarré` sur une base sans le 002, et la
   question sans réponse de 10:26:24 (« ticket-003 dépend de ticket-002, qui
   n'est pas fait »). C'est la cause décrite par ticket-451.
6. La PR a été mergée à 11:08:35 UTC (commit de squash `(#14)` sur la base du
   projet) sans ligne `merge_effectue` côté Tessera : à la main.

Conséquence pour ce ticket : la correction livrée ici arrête une PR
**surveillée** qui devient `dirty` pendant l'attente de CI. Elle n'aurait pas
changé le sort de la PR #14, qui n'était pas surveillée. Ce que #14 réclamait
est ticket-451 (ne pas démarrer un dépendant sur une réponse par défaut) ;
la ligne « confiée au CIWatcher » écrite sans watcher est ticket-455.