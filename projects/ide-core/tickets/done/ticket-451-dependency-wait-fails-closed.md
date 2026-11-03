---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 1
id: ticket-451
plan: true
pr_number: 464
priority: high
status: done
title: A queue waits for the real merge of a dependency, never for a default answer
type: fix
---

# ticket-451 — L'attente d'une dépendance échoue fermée

## Objectif

Dans une file, un ticket qui déclare `depends_on` ne démarre qu'une fois la
PR de sa dépendance réellement mergée (ADR-051).

## Contexte

Signalé par make-your-call le 15/10 (file c74dce05) : ticket-003 déclare
`depends_on: [ticket-002]`. Journal :

```
10:20:56 [make-your-call] ticket-002 : base réalignée sur main
10:20:56 [make-your-call] ticket-002 PR #14 confiée au CIWatcher
10:21:01 [ticket-003] tour 1 — codeur démarré
```

La PR #14 n'était pas mergée. Le 003 est parti d'une base sans le 002 :
son testeur a échoué sur un champ que crée le 002, le codeur l'a recréé
(migration en double), et la PR #14 est devenue CONFLICTING.

Dans `backend/src/tessera/services/orchestrator.py`, `_attendre_si_dependant`
appelle `CIWatcher.attendre_merge`. Dans
`backend/src/tessera/services/ci_watcher.py`, `attendre_merge` renvoie
`True` (« mergé ») **par défaut** quand le ticket n'est pas dans
`_en_attente` — « safe default ». La ligne « base réalignée » prouve que
c'est ce `True` qui a été reçu : le 002 n'était pas, ou plus, inscrit au
moment de l'appel. Le plan doit établir pourquoi (ordre entre l'appel à
`surveiller` depuis `backend/src/tessera/routers/orchestrator.py` et le
retour du résultat à la file, clé de projet, ou fin immédiate de la tâche).

## Solution proposée

- Trouver et corriger la cause de l'absence d'inscription.
- Quelle qu'elle soit, `attendre_merge` ne répond plus « mergé » par
  défaut pour un ticket dont on connaît le numéro de PR : sans inscription
  ni résultat enregistré, il relit l'état de la PR (`pr_state`) et ne rend
  `True` que si elle est `merged`.

## Critères d'acceptation

- [ ] Un test reproduit la séquence : livraison d'un ticket avec PR, ticket
      suivant qui en dépend ; le ticket suivant ne démarre pas tant que la
      PR n'est pas mergée
- [ ] Un test vérifie qu'`attendre_merge` sur un ticket non inscrit dont la
      PR est ouverte ne rend pas `True`
- [ ] Un test vérifie qu'`attendre_merge` sur un ticket non inscrit dont la
      PR est mergée rend `True`
- [ ] La cause de l'absence d'inscription est décrite dans la PR

## Ce que ça ne fait pas

- Ne répare pas la PR #14 de make-your-call (fait à la main).