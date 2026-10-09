---
agent: codeur
created: 2026-10-09
depends_on: []
estimated_days: 0.5
id: ticket-392
pr_number: null
priority: high
status: done
title: CIWatcher never edits a ticket file in the working tree when it blocks a PR
type: fix
---

# ticket-392 — CIWatcher ne modifie plus une fiche dans l'arbre de travail

## Objectif

Qu'un merge refusé en phase 2 ne laisse aucune modification dans l'arbre de
travail du projet, et qu'aucune fiche de ticket ne passe dans la branche d'un
autre ticket.

## Contexte

Quand la phase 2 de livraison échoue (CI rouge, CI absente, merge refusé),
`CIWatcher._bloquer_ticket` (`backend/src/tessera/services/ci_watcher.py`)
appelle `ticket_svc.update_status(ticket_id, blocked)`, qui déplace la fiche
dans `tickets/blocked/` **dans l'arbre de travail**, quelle que soit la
branche active. La phase 2 tourne en fond (ADR-051) : à ce moment-là, la file
a déjà démarré le ticket suivant sur sa propre branche.

Constaté le 2026-10-09 à 12:54 UTC : la PR #337 (ticket-387) est refusée
(« CI none », après un push qui relançait la CI) ; la fiche du 387 passe en
`blocked/` sur la branche du ticket-388, en cours. Le commit du 388 l'a
embarquée, et sa livraison s'est arrêtée sur un conflit de renommage avec
develop, où le 387 venait d'être mergé `done`.

## Solution proposée

1. `CIWatcher` ne modifie plus la fiche du ticket : il ne prend plus de
   `ticket_svc` pour changer un statut, ou ne l'appelle plus.
2. Le blocage reste visible par ce qui existe déjà : la ligne de
   `memory/pipeline-log.md` (`_ecrire_log_blocage`), l'événement
   `ticket_status_changed` (`blocked`) pour le tableau, et `attendre_merge`
   qui rend `False` pour bloquer les dépendants (ticket-384).
3. La PR reste ouverte, comme aujourd'hui.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_ci_watcher.py` fait échouer la phase 2 et vérifie qu'aucun fichier de `tickets/` n'a été déplacé ni modifié dans le dossier du projet
- [ ] Un test de `backend/tests/test_ci_watcher.py` vérifie que l'échec de phase 2 émet toujours `ticket_status_changed` avec le statut `blocked` et écrit sa ligne dans `memory/pipeline-log.md`
- [ ] Un test de `backend/tests/test_ci_watcher.py` vérifie que `attendre_merge` rend toujours `False` après un échec de phase 2
- [ ] Aucun appel à `update_status` ne subsiste dans `backend/src/tessera/services/ci_watcher.py`

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

La fiche du ticket reste `todo` sur la base tant que sa PR n'est pas mergée,
et `done` sur sa branche : le tableau s'appuie sur l'événement et sur le
journal pour montrer le blocage. Un rechargement de la page perd cet état ;
le journal le garde.

## Ce que ça ne fait pas

- Ne change pas le délai de grâce de la CI (`_GRACE_CI_S`, livraison).
- Ne relance pas la CI ni le merge.