---
agent: codeur
created: 2026-10-09
depends_on: []
estimated_days: 1
id: ticket-391
pr_number: 348
priority: medium
status: done
title: The delivery rebase merges the pipeline log and the documentation list as a
  union instead of stopping
type: fix
---

# ticket-391 — Le rebase de livraison fusionne le journal en union

## Objectif

Que deux tickets successifs d'une file ne s'arrêtent plus en livraison sur
un conflit dans des fichiers où chacun ne fait qu'ajouter.

## Contexte

Depuis le ticket-378, chaque ticket commite `memory/pipeline-log.md` sur sa
branche, et la documentation par lot (ADR-035) écrit
`memory/documentation.json`, la liste des tickets documentés. Le ticket
suivant part d'une base qui ne contient pas encore ces ajouts. Au rebase de
livraison (`GitWorkspaceService`, `backend/src/tessera/services/git_workspace.py`),
les deux côtés ont ajouté des lignes : conflit, livraison arrêtée
(« Conflit avec main sur : memory/pipeline-log.md »).

Signalé par la session qui pilote vigie, le 2026-10-09 à 12:33 UTC (vigie,
ticket-016). Le ticket-382 évite ce cas sur un projet en
`merge_without_ci: true`, mais pas sur un projet qui attend sa CI
(ide-core). Le résolveur de conflits (ADR-033) ouvre alors une PR à relire
pour un simple journal.

## Solution proposée

1. Pendant le rebase de livraison, quand les seuls fichiers en conflit sont
   `memory/pipeline-log.md` et/ou `memory/documentation.json` :
   - `pipeline-log.md` : union des deux versions (`git merge-file --union`
     sur les trois étapes de l'index), les lignes de la base d'abord ;
   - `documentation.json` : union des listes, sans doublon, dans l'ordre de
     la base puis du ticket ; un JSON illisible d'un côté laisse le conflit
     tel quel.
   Puis `git add` et `rebase --continue`, et l'étape est journalisée :
   « conflit de journal résolu en union ».
2. Si un autre fichier est aussi en conflit, le comportement actuel ne
   change pas (arrêt ou `resolveur-conflit`, ADR-033).

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_git_workspace.py` crée, dans un vrai dépôt temporaire, deux branches qui ajoutent chacune une ligne différente à `memory/pipeline-log.md` et vérifie que le rebase de livraison aboutit avec les deux lignes présentes
- [ ] Un test de `backend/tests/test_git_workspace.py` vérifie qu'un conflit sur `memory/documentation.json` entre deux listes se résout en union sans doublon
- [ ] Un test de `backend/tests/test_git_workspace.py` vérifie qu'un conflit qui touche aussi un autre fichier (par exemple `docs/architecture.md`) n'est pas résolu automatiquement et rend la liste des fichiers en conflit, comme aujourd'hui
- [ ] Un test de `backend/tests/test_git_workspace.py` vérifie qu'un `documentation.json` illisible d'un côté laisse le conflit non résolu

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Une union garde les deux versions d'une ligne modifiée des deux côtés : le
journal ne fait qu'ajouter, mais une ligne réécrite apparaîtrait deux fois.
C'est acceptable pour un journal ; c'est pour cela que seuls ces deux fichiers
sont concernés.

## Ce que ça ne fait pas

- Ne résout pas les conflits de `docs/` : ils restent à relire.
- N'installe pas de merge driver dans `.gitattributes` des projets : la
  résolution reste dans Tessera, sans toucher au dépôt du client.