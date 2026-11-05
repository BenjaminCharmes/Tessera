---
id: ticket-826
title: "The architecture test knows the services domains"
type: test
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-05
---

# ticket-826 — Le test d'architecture connaît les domaines de `services/`

## Objectif

Le sens des imports entre domaines de `services/` se mesure, avant que le premier module
ne bouge, et un module nouveau ne peut plus naître sans domaine.

## Contexte

ADR-076 et `memory/services-domaines.md` (ordre des domaines, classement des 207 modules).
`backend/tests/test_sens_des_imports.py` ne connaît aujourd'hui que `models > services > routers`
(ticket-670, cliquet `ECARTS_CONNUS`). Ce ticket n'en change pas les règles : il ajoute celles des
domaines à côté, sans déplacer de module.

## Ce que le ticket fait

- `scripts/domaines_services.py` (données seules, sans import de `tessera`) :
  `ORDRE: tuple[str, ...]` (les dix-huit domaines, du plus bas au plus haut) et
  `A_DEPLACER: dict[str, str]` (module à plat → domaine), recopiés du fichier de mémoire.
- `backend/tests/test_domaines_services.py`, qui lit ce module et réutilise les fonctions
  d'analyse d'imports de `test_sens_des_imports.py` (les sortir dans `backend/tests/_imports.py`
  si l'import entre tests ne tient pas ; ce fichier-là ne change pas de comportement) :
  - le domaine d'un module est son dossier (`services/<domaine>/…`) ou, pour un module à plat,
    sa ligne de `A_DEPLACER` ;
  - un module n'importe que son domaine ou un domaine de rang plus bas ; `routers/` importe tout ;
    les imports paresseux et ceux sous `TYPE_CHECKING` comptent ;
  - `from tessera.services import x` se résout comme `tessera.services.x` ;
  - couverture : tout `services/*.py` à plat figure dans `A_DEPLACER` (sauf `__init__.py`), toute
    entrée de `A_DEPLACER` désigne un fichier existant ;
  - aucun paquet de premier niveau de `tessera/` hors `models`, `services`, `routers`, `utils` ;
    `agents` est toléré par `PAQUETS_TOLERES`, que le ticket-816 vide.
- `ECARTS_DOMAINES` : les écarts mesurés à l'ouverture, au format `chemin -> domaine importé`,
  avec la même règle de cliquet qu'`ECARTS_CONNUS` (un écart corrigé se retire, aucun ne s'ajoute).
- Avant de lister un écart, reclasser : si le même couple de domaines en porte trois, ou si un seul
  déplacement de module le supprime, c'est le classement de `A_DEPLACER` qui se corrige, pas la liste.
  Un reclassement s'écrit dans le message de commit.

## Tests (`backend/tests/test_domaines_services.py`)

Sur des arbres temporaires, comme `test_sens_des_imports.py` :

- `test_import_to_a_lower_domain_passes`, `test_import_to_a_higher_domain_fails`
- `test_flat_module_domain_comes_from_the_table`, `test_package_domain_comes_from_its_folder`
- `test_from_services_import_module_is_resolved`
- `test_type_checking_and_lazy_imports_count`
- `test_undeclared_flat_module_fails`, `test_table_entry_without_file_fails`
- `test_unknown_top_level_package_fails`, `test_tolerated_package_passes`
- `test_listed_gap_passes_while_it_exists`, `test_listed_gap_already_fixed_fails`
- `test_real_tree_follows_the_domains` : l'arbre réel, `ECARTS_DOMAINES` à la main

## Critères d'acceptation

- [ ] `scripts/domaines_services.py` porte les dix-huit domaines dans l'ordre d'ADR-076 et un
      domaine pour chaque module à plat du dossier
- [ ] `test_real_tree_follows_the_domains` passe sur l'arbre réel
- [ ] Un module à plat ajouté sans ligne dans `A_DEPLACER` fait échouer ce test
- [ ] Aucun module de `services/` n'a bougé, aucun import n'a changé

## Ce que ça ne fait pas

Aucun déplacement (tickets 803 et suivants), aucun outil de déplacement (ticket-827). Aucune règle
pour `utils/`.

## Risques

`test_sens_des_imports.py` est un test existant : le ticket n'affaiblit aucune de ses règles. Si
plus de quinze écarts remontent, le classement est faux plutôt que le code : le dire dans le commit.
