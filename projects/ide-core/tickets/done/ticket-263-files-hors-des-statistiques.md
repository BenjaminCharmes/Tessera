---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 1
id: ticket-263
pr_number: null
priority: medium
status: done
title: Queue and autonomous run containers stay out of run statistics
type: fix
---

# ticket-263 — Une file n'est pas un run dans les statistiques

## Objectif

Que les statistiques ne comptent que les runs de tickets, pas l'enveloppe d'une
file ou d'un run autonome.

## Contexte

Constaté le 2026-09-30 dans « Runs récents » (vue Statistiques) : chaque file
apparaît comme une ligne à part, en plus des runs de ses tickets —
`ticket-259, ticket-260`, `0 / 0` tokens, `0 $`, durée égale à la file entière,
« approuvé ».

Deux écritures coexistent dans `pipeline_runs` :
- `run_executor.executer` (`services/run_executor.py`) crée une ligne pour
  **chaque** run lancé, file et autonome compris, avec `run.ticket_id or
  run.mode` : c'est elle qui porte les événements du canal (ADR-041) ;
- `RunRecorder` (`services/run_recorder.py`) crée une ligne **par ticket**
  exécuté dans cette file.

La ligne d'enveloppe est légitime pour les événements, mais
`services/usage_stats.py` et les requêtes de `services/database.py` la lisent
comme un run : elle entre dans `recent_runs`, et vraisemblablement dans le
nombre de runs et le taux d'aboutissement (`quality`).

## Solution proposée

- Ajouter à `pipeline_runs` une colonne `mode` (`single`, `queue`,
  `autonomous`), renseignée à la création ; migration idempotente, comme les
  colonnes ajoutées avant elle dans `database.py`. Les lignes existantes
  restent `NULL`, lues comme `single`.
- `executer` passe `run.mode` ; `RunRecorder` écrit `single`.
- Les requêtes de statistiques (`recent_runs`, totaux de runs, `quality`)
  excluent les lignes `queue` et `autonomous`. Les coûts et tokens ne changent
  pas : ils sont rattachés aux appels d'agents, pas à la ligne d'enveloppe — le
  vérifier, et le dire en commentaire.
- Ne pas supprimer la ligne d'enveloppe : l'historique des événements en dépend.

## Critères d'acceptation

- [ ] `pipeline_runs` a une colonne `mode`, ajoutée par une migration qui peut
      tourner deux fois sans erreur (test).
- [ ] Un test montre qu'une ligne créée par `executer` en mode `queue` porte
      `mode = 'queue'`.
- [ ] Un test montre que `recent_runs` ne contient pas une ligne de mode
      `queue`, alors qu'il contient les runs de ses tickets.
- [ ] Un test montre que le nombre total de runs des statistiques ne compte pas
      les lignes de mode `queue` ni `autonomous`.

## Dépendances

Aucune.

## Estimation

1 jour. Backend uniquement.

## Risques

- Les anciennes lignes d'enveloppe (avant migration) ont `mode = NULL` et
  resteraient visibles. Les reconnaître à leur `ticket_id` (liste séparée par
  des virgules, ou `queue` / `autonomous`) dans la migration, pour leur poser
  le bon `mode` — sans deviner au-delà.