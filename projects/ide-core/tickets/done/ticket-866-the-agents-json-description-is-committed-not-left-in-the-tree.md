---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 1
id: ticket-866
pr_number: 950
priority: high
status: done
title: The agents.json description written by the documentation is committed, not
  left in the tree
type: fix
---

# ticket-866 — La description d'`agents.json` écrite par la documentation est commitée

## Objectif

Une description d'`agents.json` acceptée par le service de documentation (ADR-068) part dans
le commit de documentation du run ; elle ne reste jamais non commitée dans l'arbre.

## Contexte

Le 06/11 à 00 h 43, la file ide-core s'est interrompue sur le ticket-857 approuvé : « Rebase
refusé : cannot rebase: You have unstaged changes ». Le service de documentation avait réécrit
la clé `description` de `projects/ide-core/agents.json` (`documentation_description.py`,
`ecrire_description`), puis `_commiter` (`services/pipeline/pipeline_documentation.py`) a
appelé `commit_all`, qui **exclut** les fichiers de politique du run (`_RUN_POLICY_PATHS`,
`services/git_workspace/commits.py`, ticket-296) : `agents.json` est resté modifié, et la
livraison a refusé l'arbre sale.

Les deux règles sont justes séparément : une modification d'`agents.json` faite pendant le
run par l'interface ne doit pas partir avec le travail du codeur (ticket-296) ; la description
proposée par doc-technique et contrôlée doit, elle, être versionnée (ADR-068).

## Solution proposée

- Quand le lot de documentation a écrit la description (le chemin d'`agents.json` figure dans
  `lot.fichiers`), `_commiter` la commite explicitement : ajout nommé de ce seul fichier, puis
  le commit de documentation du run. Le reste de `commit_all` ne change pas.
- Si `agents.json` portait **déjà** une modification avant l'écriture de la description
  (changement fait par l'interface pendant le run), la description n'est pas écrite : refus
  journalisé dans `lot.refus` (« agents.json modifié pendant le run »), comme les autres refus.

## Critères d'acceptation

- [ ] Un test vérifie, sur un dépôt temporaire, qu'après une description acceptée l'arbre est
      propre et que le dernier commit contient la nouvelle `description` d'`agents.json`
- [ ] Un test vérifie qu'une modification d'`agents.json` présente avant le lot fait refuser la
      description, laisse cette modification hors de tout commit et l'ajoute à `lot.refus`
- [ ] Le diff ne modifie ni `_RUN_POLICY_PATHS` ni le comportement de `commit_all` pour les
      autres appels (le test existant de ticket-296 passe sans modification)

## Risques

Touche la livraison (arbre propre, ADR-018) : un commit en trop vaut mieux qu'un arbre sale,
qui interrompt toute la file.