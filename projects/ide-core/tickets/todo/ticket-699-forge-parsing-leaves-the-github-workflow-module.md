---
id: ticket-699
title: "Forge parsing leaves the GitHub workflow module"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-699 — L'analyse du remote quitte `github_workflow.py`

## Objectif
`parse_remote` et les noms de forge vivent dans leur module : ils n'ont aucun
lien avec l'ouverture ni le merge d'une PR.

## Contexte
`services/github_workflow.py` (520 lignes), 444-520 : `_forge_depuis_hote`,
`parse_remote`, `nom_de_la_forge`, `forge_supportee`, des fonctions pures.
`project_loader.py:159` les importe à l'intérieur d'une fonction
(`docs/audit/refactos.md` §2.1) ; elles ne dépendent pas du reste du module.

## Critères d'acceptation
- [ ] `grep -rn "def parse_remote" backend/src` ne rend que le module neuf
- [ ] Tous les importeurs sont mis à jour ; l'import de `project_loader.py:159` peut passer en tête de fichier, et si Python proteste (cycle), la PR le dit au lieu de le contourner
- [ ] L'entrée de `services/github_workflow.py` dans `PLAFONDS` est baissée à 450 ou moins
- [ ] Les tests de `parse_remote` passent sans changement de leurs attendus
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne touche ni aux protocoles locaux ni aux méthodes de passage entre `GitHubService`, `GitHubWorkflowService` et `LivraisonService` : ce correctif attend le ticket-677 et une décision de frontière
