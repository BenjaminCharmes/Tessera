---
agent: codeur
created: 2026-10-07
depends_on:
- ticket-375
estimated_days: 0.5
id: ticket-377
pr_number: null
priority: high
status: done
title: A queue that dies writes it in the pipeline log, and a recovered ticket branch
  always keeps its ticket file
type: fix
---

# ticket-377 — Une file qui meurt le dit, et une branche reprise garde sa fiche

## Objectif

Qu'une file arrêtée par une exception soit visible dans le journal du
pipeline, et qu'une branche de ticket reprise au démarrage puisse toujours
être relancée.

## Contexte

Deux défauts constatés le 2026-10-07 sur affut, après le redémarrage de
12:18, et signalés par la session qui suit ce projet.

**1. La fiche disparaît de la branche reprise.** Au démarrage d'un run, la
fiche passe de `tickets/todo/` à `tickets/in-progress/` : ce nouveau chemin
n'est pas encore suivi par git. La reprise (`reprise_orphelin.py`, tickets
369 et 375) ne commite que les fichiers suivis : son commit « unapproved
work » a enregistré la suppression de `tickets/todo/ticket-004-….md` sans
l'ajout dans `in-progress/`. Sur la branche, la fiche n'existait plus ; le run
suivant a repris la branche et s'est arrêté sur
`run_interrompu: Ticket introuvable : ticket-004` (12:21:26).

Le ticket-375 remet la fiche en `todo` sur la branche du ticket avant le
commit, ce qui devrait couvrir ce cas : ce ticket en pose le test, quel que
soit le dossier de statut d'origine.

**2. Une file qui meurt ne laisse aucune trace.** Dans
`backend/src/tessera/services/run_executor.py`, une exception est journalisée
(`run_interrompu`) dans `tessera.log`, mais aucune ligne n'est écrite dans
`memory/pipeline-log.md`. Vu de l'IDE, la file semblait tourner alors qu'elle
était arrêtée depuis 17 minutes. Les autres arrêts de file
(`orchestrator.py`) écrivent déjà `[projet] file interrompue : …`.

## Solution proposée

1. Un test de reprise couvre une fiche déplacée dans `in-progress/` ou
   `in-review/` et non suivie : après la reprise, la branche du ticket
   contient la fiche. Si le ticket-375 ne suffit pas, la reprise ajoute
   explicitement le fichier de la fiche (et lui seul) au commit.
2. Quand `run_executor` attrape une exception, il écrit dans le journal du
   pipeline du projet une ligne `[<projet>] file interrompue : <erreur>`, par
   le même mécanisme que les autres arrêts de file.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` simule une fiche déplacée de `tickets/todo/` vers `tickets/in-progress/` sans l'ajouter à git, lance la reprise, et vérifie que le dernier commit de la branche du ticket contient une fiche de ce ticket
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie la même chose pour une fiche déplacée vers `tickets/in-review/`
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'aucun autre fichier non suivi n'entre dans le commit de reprise
- [ ] Un test de `backend/tests/test_run_executor.py` fait lever une exception au pipeline et vérifie que `memory/pipeline-log.md` du projet contient une ligne `file interrompue` qui reprend le message de l'erreur

## Dépendances

ticket-375 (remise en `todo` sur la branche du ticket).

## Estimation

0,5 jour.

## Risques

Aucun : le commit de reprise n'embarque que la fiche du ticket en plus des
fichiers suivis.

## Ce que ça ne fait pas

- Ne relance pas une file morte.