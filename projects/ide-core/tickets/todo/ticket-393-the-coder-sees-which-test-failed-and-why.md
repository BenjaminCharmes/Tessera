---
id: ticket-393
title: "The coder sees which test failed and why, and the log shows the real test summary"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-09
---

# ticket-393 — Le codeur voit quel test échoue et pourquoi

## Objectif

Qu'après des tests rouges, le codeur reçoive le nom du test en échec et son
assertion, et que le journal affiche le vrai résumé de pytest.

## Contexte

`backend/src/tessera/services/test_runner.py` réduit la sortie des tests à
deux éléments, transmis au codeur par `pipeline_stages.py` (section
« Résultats des tests ») et écrits dans le journal :

- `_extract_summary_line` : la **dernière** ligne qui contient « passed »,
  « failed », « error », « ok » ou « test ». Une ligne de warning en fin de
  sortie passe devant le résumé de pytest.
- `_extract_errors` : les **cinq premières** lignes contenant « FAILED »,
  « ERROR » ou « ASSERT », prises n'importe où dans la sortie.

Signalé par la session qui pilote vigie le 2026-10-09 (ticket-018, run
9fbc0f24, 13:21-13:25 UTC). Un seul test échouait :
`assert await migrate(conn) == [5]` donnait `[5, 6]`, et 455 tests
passaient. Le journal affichait « testeur: res = hook_impl.function(*args) »,
la fin d'un warning. Le codeur a tourné deux fois sans corriger cette
assertion, et le ticket a fini en `blocked` après trois tours.

## Solution proposée

1. **Résumé** : chercher d'abord la ligne de résumé de pytest
   (`=… N failed, M passed … in X.XXs …=`) ou de vitest
   (`Tests  N failed | M passed`) ; ne retomber sur l'heuristique actuelle
   qu'à défaut.
2. **Détail pour le codeur** : un nouveau champ de `TestResult`
   (`failure_details: str`) qui contient, dans cet ordre :
   - la section « short test summary info » de pytest (les lignes
     `FAILED …` / `ERROR …`), sinon les lignes `FAIL`/`×` de vitest ;
   - la section `FAILURES` / `ERRORS` de pytest, ou le bloc d'échec de
     vitest, **tronquée à 8 000 caractères**, en gardant le début de chaque
     échec (nom du test, lignes `E   …`) plutôt que la fin de la sortie.
3. `pipeline_stages.py` transmet `failure_details` au codeur dans la section
   « Résultats des tests », à la place de la liste `errors` quand il est
   non vide. Le journal garde une seule ligne : le résumé.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_test_runner.py` analyse une sortie pytest réelle (un test en échec, 455 passés, puis un `UserWarning` en dernière ligne) et vérifie que `output_summary` est la ligne `1 failed, 455 passed`, et non le warning
- [ ] Un test de `backend/tests/test_test_runner.py` vérifie que `failure_details` contient la ligne `FAILED tests/test_migration_story.py::…` et la ligne `E       assert [5, 6] == [5]` de cette même sortie
- [ ] Un test de `backend/tests/test_test_runner.py` vérifie que `failure_details` ne dépasse pas 8 000 caractères pour une sortie de 50 échecs, et qu'il commence par la section « short test summary info »
- [ ] Un test de `backend/tests/test_test_runner.py` analyse une sortie vitest en échec et vérifie que le résumé et le nom du test en échec sont extraits
- [ ] Un test de `backend/tests/test_testeur_enchaine.py` vérifie que le prompt du tour suivant du codeur contient `failure_details`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un prompt plus long au tour suivant (8 000 caractères au plus) : c'est peu
par rapport à un tour complet perdu (environ six minutes de suite et un
appel du codeur).

## Ce que ça ne fait pas

- Ne change pas la commande de test ni `scripts/verifier.py`.
- Ne transmet pas la sortie complète : seulement ce qui décrit l'échec.
