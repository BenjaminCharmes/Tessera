---
id: ticket-792
title: "An approved ticket whose delivery failed is reported as undelivered and retried at the end of the queue"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-11-04
---

# ticket-792 — Un ticket approuvé dont la livraison a échoué est signalé comme non livré et relivré en fin de file

## Objectif

Le travail approuvé d'un ticket ne reste jamais sur une branche locale sans que personne ne le
sache.

## Contexte

04/11, file ide-core b137c303 : ticket-753 est approuvé (reviewer, audit, validateur), puis
`livraison_done` porte `arret: "Livraison interrompue : GitCommandError … push … remote: Internal
Server Error"`. Aucune branche distante, aucune PR. La file a continué et compté 753 parmi les
`approuves` de `GET /api/v1/runs/{id}` : rien ne distinguait ce ticket de ceux qui étaient
mergés. Il a été retrouvé quatre heures plus tard et livré à la main.

`livraison_arrete_la_file` (`backend/src/tessera/services/pipeline_file_livraison.py`) n'arrête
la file sur un ticket sans PR que si un ticket restant en dépend (`_sans_pr`, ticket-361).
Sinon, rien ne se passe, ce qui est voulu : une exception de livraison ne fait pas échouer le run
(ADR-030). Mais rien ne la signale ni ne la retente. Le ticket-787 retente un push refusé sur une
5xx, une seule fois et tout de suite : un incident qui dure quelques minutes le dépasse.

## Solution proposée

- Le statut d'une file (`run_status.py`, `classer_les_tickets`) range à part, dans
  `non_livres`, un ticket approuvé dont la livraison s'est arrêtée sans PR. Il n'apparaît plus
  dans `approuves`.
- L'événement `queue_progress` porte la même liste `non_livres`.
- Quand la file a passé son dernier ticket, elle relance une fois la livraison de chaque ticket
  de `non_livres` depuis sa branche locale (même chemin que la livraison normale : rebase, push,
  PR, CIWatcher). Un ticket livré à cette reprise rejoint `approuves` ; un nouvel échec le laisse
  dans `non_livres`, avec l'arrêt journalisé.
- Jamais de push forcé (ADR-022).

## Critères d'acceptation

- [ ] Un test de `classer_les_tickets` vérifie qu'un ticket approuvé dont la livraison porte un
      `arret` et aucun `pr_number` est rangé dans `non_livres` et pas dans `approuves`
- [ ] Un test vérifie que `queue_progress` porte `non_livres`
- [ ] Un test vérifie, avec des doubles, qu'en fin de file la livraison d'un ticket non livré est
      relancée une fois, et qu'un succès le fait passer dans `approuves`
- [ ] Un test vérifie qu'un second échec de livraison laisse le ticket dans `non_livres`, sans
      troisième tentative
