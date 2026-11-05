---
id: ticket-802
title: "A script moves one services domain and rewrites its references"
type: chore
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-801]
estimated_days: 1
created: 2026-11-05
---

# ticket-802 — Un script déplace un domaine de `services/` et réécrit ses références

## Objectif

Déplacer un domaine tient en une commande, sans réécriture à la main de centaines d'imports, et
sans qu'une chaîne de `monkeypatch` oubliée change un test en silence.

## Contexte

ADR-074. Les tickets 803 à 818 déplacent un domaine chacun, à comportement constant. Les agents
n'émettent aucune commande git en écriture : le script déplace par renommage de fichier, git
reconnaît la renommée à la similarité du contenu.

## Ce que le ticket fait

`scripts/deplacer_domaine.py <domaine> [--dry-run]`, qui lit `scripts/domaines_services.py`
(ticket-801) :

- crée `services/<domaine>/` avec un `__init__.py` vide s'il manque (jamais pour `providers`,
  `provisioning`, `git_workspace`, qui existent) ;
- renomme chaque module à plat du domaine dans ce dossier, et retire ses lignes de `A_DEPLACER` ;
- réécrit dans `backend/src`, `backend/tests`, `scripts/`, `Makefile` : `from tessera.services.x import`,
  `from tessera.services import x, y as z` (monoligne et entre parenthèses, une ligne par domaine
  cible), `import tessera.services.x`, `python -m tessera.services.x`, et toute chaîne littérale
  `"tessera.services.x…"` (patch, importlib) ;
- ne touche pas `tessera.services.x_suite` en réécrivant `x` : la fin du nom compte ;
- signale, sans corriger, tout `__file__` ou `parents[N]` dans un module déplacé, et tout
  `tessera.services.x` restant dans `docs/` et `projects/` (texte, laissé tel quel) ;
- `--dry-run` liste ce qui bougerait et ne modifie rien ; un domaine inconnu, ou déjà vide, sort
  en erreur.

## Tests (`backend/tests/test_deplacer_domaine.py`)

Sur un arbre temporaire :

- `test_module_is_moved_and_removed_from_the_table`
- `test_dotted_import_is_rewritten`, `test_from_package_import_is_split_by_target_domain`
- `test_parenthesised_multiline_import_is_rewritten`, `test_alias_is_kept`
- `test_string_literal_in_a_patch_is_rewritten`
- `test_python_dash_m_in_a_makefile_is_rewritten`
- `test_longer_module_name_is_not_touched`
- `test_file_based_path_in_a_moved_module_is_reported`
- `test_dry_run_changes_nothing`, `test_unknown_domain_fails`
- `test_existing_package_keeps_its_init`

## Critères d'acceptation

- [ ] `uv run python scripts/deplacer_domaine.py supervision --dry-run` liste les quatorze modules
      du domaine et n'écrit rien
- [ ] Les tests ci-dessus passent
- [ ] Aucun module de `services/` n'a bougé dans ce ticket

## Ce que ça ne fait pas

Ne déplace aucun module du dépôt réel (ticket-803 et suivants). Ne corrige pas `parents[N]` : un
chemin relatif à `__file__` se relit à la main, ticket par ticket.
