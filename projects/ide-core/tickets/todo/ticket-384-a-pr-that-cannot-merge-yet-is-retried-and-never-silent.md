---
id: ticket-384
title: "A PR whose mergeability is still being computed is retried, a failed merge is logged and blocks its dependents"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-08
---

# ticket-384 — Une PR pas encore fusionnable est réessayée, un merge raté se voit et bloque

## Objectif

Qu'une PR approuvée ne reste plus ouverte en silence pendant que la file
continue sans elle.

## Contexte

Constaté le 2026-10-07 à 14:59:52 UTC sur affut, signalé par la session qui
pilote ce projet : la PR #10 (ticket-007), approuvée, n'a jamais été mergée.
`tessera.log` porte `merge_fusionnabilite_refusee` (« La PR #10 est encore en
attente de calcul de fusionnabilité après 60 s. La livraison s'arrête. »),
puis `ci_merge_blocked`. Rien dans `memory/pipeline-log.md`. La file a
continué : cinq tickets ont été construits sans le 007.

Trois défauts :

1. `GitHubService.merge_quand_fusionnable`
   (`backend/src/tessera/services/github_service.py`) abandonne après
   `attente_max_s` = 60 s quand `mergeable` vaut encore `null`. Ce n'est pas
   un refus : GitHub calcule, souvent plus longtemps juste après un merge
   précédent sur la même base.
2. `CIWatcher._livrer_et_emettre` (`backend/src/tessera/services/ci_watcher.py`)
   émet bien un événement `blocked`, mais n'écrit aucune ligne dans le
   journal du pipeline, et la fiche du ticket ne change pas de dossier.
3. `ci_watcher.attendre_merge` rend la main dès que le ticket n'est plus en
   attente, **mergé ou bloqué** : un ticket qui en dépend
   (`_attendre_si_dependant`, `orchestrator.py`) démarre alors sans sa
   dépendance, à rebours de l'intention du ticket-361.

## Solution proposée

1. Porter l'attente de fusionnabilité à `attente_fusionnabilite_max_s`
   (réglage, 300 s par défaut), avec un délai entre deux lectures qui croît.
2. Quand le merge échoue, écrire
   `[<ticket>] livraison: arrêt — PR #N non mergée : <raison>` dans
   `memory/pipeline-log.md` et passer la fiche en `blocked` (dossier **et**
   champ).
3. `attendre_merge` indique si le ticket a été mergé ; si sa dépendance n'a
   pas été mergée, la file ne lance pas le ticket dépendant et s'arrête avec
   `[<projet>] file interrompue : <ticket> non mergé`.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_github_service.py` simule `mergeable` à `null` pendant 90 s puis `true`, et vérifie que `merge_quand_fusionnable` merge sans lever (horloge et sommeil simulés)
- [ ] Un test de `backend/tests/test_github_service.py` vérifie qu'au-delà de `attente_fusionnabilite_max_s` l'erreur de délai est levée
- [ ] Un test de `backend/tests/test_ci_watcher.py` vérifie qu'un merge raté écrit une ligne `PR #… non mergée` dans `memory/pipeline-log.md` du projet et passe la fiche du ticket dans `tickets/blocked/` avec `status: blocked`
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie qu'une file dont le ticket B dépend de A ne lance pas B quand le merge de A échoue, et écrit `file interrompue : ticket-… non mergé`
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie qu'un ticket indépendant de A garde le comportement actuel

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Une PR réellement en conflit est détectée par `mergeable: false`, pas par le
délai : elle reste traitée tout de suite comme aujourd'hui.

## Ce que ça ne fait pas

- Ne rebase pas une PR devenue non fusionnable.
- Ne ferme pas la PR : elle reste ouverte pour l'utilisateur.
