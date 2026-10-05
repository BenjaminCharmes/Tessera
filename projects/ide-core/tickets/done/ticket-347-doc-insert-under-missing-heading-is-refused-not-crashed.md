---
id: ticket-347
title: "An insertion under a heading that no line starts with is refused, not a crash of the documentation batch"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.25
created: 2026-10-05
---

# ticket-347 — Une section introuvable se refuse, elle ne fait pas tomber le lot

## Objectif

Qu'une insertion visant un titre absent soit refusée comme toute autre
édition invalide, avec un motif lisible dans `pipeline-log.md`.

## Contexte

Le 2026-10-05, la documentation du ticket-343 a échoué ainsi :

    [ticket-343] documentation: échec — coroutine raised StopIteration

La cause est dans `_inserer` (`backend/src/tessera/services/documentation.py`) :

- la garde teste `section in avant` — la section présente **n'importe où**
  dans le texte, même au milieu d'une ligne ;
- la ligne suivante cherche `next(i for i, l in enumerate(lignes) if
  l.startswith(section))` — une ligne qui **commence** par la section, sans
  valeur par défaut.

Quand l'agent vise `## Supervision` et que le fichier porte
`### Supervision` (ou le titre cité dans une phrase), la garde passe, `next`
lève `StopIteration`, et Python la convertit en
`RuntimeError: coroutine raised StopIteration` en remontant la coroutine.
Ce n'est pas une `EditionRefusee` : le lot entier tombe dans le
`except Exception` de `_documenter_le_run`
(`backend/src/tessera/services/orchestrator.py`), avec un message qui ne dit
rien de la vraie raison.

## Solution proposée

Dans `_inserer`, chercher la ligne de début avec `next(..., None)` et lever
`EditionRefusee(f"{chemin} : section « {section} » introuvable.")` quand
aucune ligne ne commence par la section. La garde `section in avant`
devient alors inutile et peut disparaître : un seul test décide.

Ne pas changer le reste du traitement d'une `EditionRefusee` : il est déjà
celui des autres éditions refusées (ticket-342).

## Critères d'acceptation

- [x] Un test de `backend/tests/test_documentation.py` montre qu'une
      insertion avec `apres_section: "## Supervision"` dans un texte qui ne
      porte que `### Supervision` lève `EditionRefusee`, et non
      `StopIteration` ni `RuntimeError`
- [x] Un test de `backend/tests/test_documentation.py` montre qu'une
      insertion dont la section n'apparaît qu'au milieu d'une phrase lève
      `EditionRefusee`
- [x] Le message de l'`EditionRefusee` contient le chemin et la section visée
- [x] Un test existant d'insertion réussie dans `test_documentation.py`
      passe toujours sans modification
- [x] `_inserer` n'appelle plus `next` sans valeur par défaut
- [x] Aucun fichier sous `frontend/` n'est modifié

## Ce que ça ne fait pas

- N'essaie pas de deviner le bon titre (niveau différent, casse, espaces) :
  une édition qui vise mal se refuse, l'agent la refera au lot suivant.
- Ne change pas ce qui suit une `EditionRefusee` en aval de `_inserer`.

## Dépendances

Aucune.

## Estimation

Un quart de journée.

## Risques

Aucun identifié : le changement ne touche qu'un chemin qui plante déjà.
