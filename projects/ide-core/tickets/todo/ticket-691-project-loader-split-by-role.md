---
id: ticket-691
title: "Project loader split into reading, writing and text extraction"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: [ticket-675]
created: 2026-10-29
---

# ticket-691 — `project_loader.py` : écriture, extraction et gabarits à part

## Objectif
Le module ne porte plus que le chargement d'un projet ; l'écriture du
manifeste, l'extraction depuis `CLAUDE.md` et les gabarits par défaut ont
chacun leur fichier.

## Contexte
`services/project_loader.py` (646 lignes) : écrivains du manifeste
(`set_agent_model`, `set_agent_provider`, `set_pipeline_settings`,
`_ecrire_manifeste` : 541-646), extraction depuis `CLAUDE.md` et le README
(339-458), gabarits (459-540). Le ticket-675 remplace d'abord les sept
lecteurs du manifeste ; découper avant ferait migrer sept copies.

## Critères d'acceptation
- [ ] L'entrée de `services/project_loader.py` disparaît de `PLAFONDS`, ou y est baissée à 350 ou moins, chaque module neuf restant sous 300
- [ ] `grep -rn "def set_agent_model\|def set_pipeline_settings" backend/src` ne rend qu'un module d'écriture
- [ ] `ProjectLoader.list_projects()` ne liste toujours que les dossiers avec un `CLAUDE.md`, et `Project.name` vient du premier `# Titre` (ADR-006, ADR-007) : les tests existants passent sans changement
- [ ] La fonction de module `list_projects` reste importable (contrainte en vigueur)
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne change pas le format d'`agents.json`
- Ne rend pas l'écriture du manifeste atomique ou verrouillée (`git_link.py:199` écrit déjà sans verrou : décision à part)
