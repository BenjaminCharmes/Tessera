---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-742
pr_number: null
priority: medium
status: done
title: Git workspace test doubles share a base with no-op defaults
type: test
---

# ticket-742 — Les doubles du workspace git partagent une base aux défauts neutres

## Objectif

Ajouter une méthode au `GitWorkspaceService` ne casse plus, un par un, les doubles des
tests qui ne s'en servent pas.

## Contexte

03/11, ticket-736 : trois tours de pipeline perdus. L'orchestrateur appelait une
nouvelle méthode du workspace ; à chaque tour la suite complète trouvait un autre
double sans elle (`AttributeError`), le codeur en corrigeait un, le suivant tombait.
Douze fichiers de tests déclarent leur propre double (`is_clean`, `commit_all`…) :
`test_arret_de_run.py`, `test_chat_service.py`, `test_commit_integrite.py`,
`test_commit_sur_toutes_les_sorties.py`, `test_contraintes_proposees.py`,
`test_emetteur_tolerant.py`, `test_limite_de_session.py`,
`test_livraison_arbre_sale.py`, `test_orchestrator.py`, `test_pipeline_stages.py`,
`test_preparation_worktree.py`, `test_runs_persistes.py`.

## Solution proposée

- Un module `backend/tests/doubles_git.py` porte une classe de base dont chaque
  méthode asynchrone appelée par l'orchestrateur et la livraison sur le workspace
  rend une valeur neutre (`None`, `True`, liste vide…).
- Chaque double des douze fichiers en hérite et ne garde que ce qu'il redéfinit
  vraiment. Aucun test ne change de comportement.

## Critères d'acceptation

- [ ] `backend/tests/doubles_git.py` définit la classe de base, et un test vérifie
      qu'elle porte chaque méthode publique asynchrone de `GitWorkspaceService` appelée
      par `services/orchestrator.py` (liste écrite dans le test)
- [ ] Les doubles des douze fichiers cités héritent de cette base
- [ ] Le diff ne modifie aucun fichier sous `backend/src/`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

- Une valeur neutre mal choisie changerait un test qui comptait sur l'absence de la
  méthode : chaque double garde ses redéfinitions existantes.