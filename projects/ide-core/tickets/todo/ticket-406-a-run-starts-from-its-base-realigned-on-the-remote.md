---
id: ticket-406
title: "A run starts from its base branch realigned on the remote, whatever the previous run left behind"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-12
---

# ticket-406 — Un run part de sa base réalignée sur le distant

## Objectif

Qu'un run ne parte jamais d'une base locale en retard sur le dépôt distant,
quel que soit l'état laissé par le run précédent.

## Contexte

Quand le dernier ticket d'une file est mergé par le CIWatcher (phase 2,
ADR-051), personne ne réaligne ensuite la base locale. Le réalignement
(`sync_base_depuis_distant`, tickets 382, 403 et #349) n'a lieu qu'entre deux
tickets d'une même file. La ligne de journal écrite après le commit de suivi
(« PR #N confiée au CIWatcher ») reste en plus non commitée sur la base. Le
run suivant, lancé plus tard, part donc de la base locale telle qu'elle est :
en retard d'un ou de plusieurs merges.

Constaté le 2026-10-12 :
- **affut** (signalé par sa session, vers 15:11 UTC) : `main...origin/main
  [behind 1]` et ` M memory/pipeline-log.md` après la PR #59 du ticket-041,
  sans résorption ;
- **habit-tracker, homelab-monitor, repo-health et Tessera** : même état,
  réparé à la main dans la journée.

C'est la cause des départs « sans la dépendance » : le 400 était parti sans le
399.

## Solution proposée

1. Au début de chaque run, avant la création de la branche
   (`stages.create_branch`, `backend/src/tessera/services/pipeline_stages.py`),
   si un espace git et une branche de base sont connus et que l'arbre est sur
   la base : appeler `sync_base_depuis_distant(base_branch)`. Elle met déjà de
   côté les lignes de journal non commitées, avance la base par
   `merge --ff-only`, puis réécrit les lignes à la suite (#349).
2. Un réalignement refusé (base locale divergente, autre fichier modifié,
   fetch impossible) n'empêche pas le run de partir. Le refus est journalisé
   (« base non réalignée — <raison> »), comme entre deux tickets.
3. Le reste ne change pas, notamment la reprise d'une branche existante.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie que `sync_base_depuis_distant` est appelé avec la branche de base avant `create_branch`, au départ d'un run seul
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie qu'un réalignement qui rend une raison de refus n'empêche pas le run de démarrer, et que la raison est écrite dans le journal
- [ ] Un test de `backend/tests/test_git_workspace.py` crée un vrai dépôt dont la base locale est en retard d'un commit sur le distant, avec une ligne de journal non commitée, et vérifie qu'après le réalignement de début de run la branche du ticket part du commit distant et que la ligne de journal est conservée
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie qu'aucun réalignement n'est tenté quand l'espace git ou la branche de base est inconnu

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Ce que ça ne fait pas

- Ne fait pas réaligner la base par le CIWatcher après le merge du dernier
  ticket : le run suivant le fera au moment où il en a besoin.
- Ne touche pas au chat (`chat_service.create_branch`).
