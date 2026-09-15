---
name: test-driven-development
description: Use when implementing any feature or bugfix in this repository, before writing implementation code — the test comes first and must be seen failing.
---

# TDD

**Si tu n'as pas vu le test échouer, tu ne sais pas ce qu'il teste.**

Un test écrit après coup passe immédiatement. Passer immédiatement ne prouve
rien : ni qu'il teste la bonne chose, ni qu'il attraperait la régression.

## Le cycle

### RED — écrire le test, le regarder échouer

Un comportement par test. Un nom qui décrit le comportement, pas la fonction.

```bash
cd backend && uv run pytest -q tests/test_x.py -k nom_du_test
```

Vérifier que l'échec est **le bon** :

- Il échoue sur l'assertion, pas sur un `AttributeError` de typo
- Le message d'échec décrit bien le comportement manquant

Si le test passe du premier coup, il teste du comportement existant. Le
reprendre.

### GREEN — le minimum pour passer

Juste assez. Pas d'options « au cas où », pas de généralisation anticipée.

```bash
uv run pytest -q tests/test_x.py     # le test cible
uv run pytest -q                     # rien d'autre n'a cassé
```

### REFACTOR — nettoyer, en restant vert

Seulement après le vert. Pas de nouveau comportement ici.

## Conventions de ce dépôt

- Tests dans `backend/tests/`, nommés **en français**
  (`test_commit_wip_quand_la_securite_bloque`), docstrings **en anglais**
- Un commentaire en tête de test qui dit **pourquoi ce cas existe** — le bug
  qu'il empêche de revenir. C'est ce qui évite qu'on le supprime dans six mois
  en le croyant redondant.
- `pytest-asyncio` en mode auto : pas de décorateur sur les tests async
- Fichiers : toujours `encoding="utf-8"` explicite. Sans lui, Windows écrit en
  cp1252 et onze tests tombent sur un accent.
- Une capacité absente de l'environnement se **skippe**, ne se contourne pas :
  voir `@requires_symlinks` dans `tests/conftest.py`

## Corriger un bug

Toujours reproduire d'abord :

1. Écrire le test qui échoue **avec le bug présent**
2. Vérifier que son message décrit bien le symptôme réel
3. Corriger
4. Le test passe, et protège contre le retour

Une correction sans test de reproduction n'est pas une correction, c'est un
espoir.

## Sortie propre

La suite doit finir sans warning. Un `PytestCollectionWarning` ou un
`DeprecationWarning` toléré aujourd'hui masque un vrai signal demain.

```
576 passed, 2 deselected in 37.49s
```

## Avant de valider

- [ ] Chaque comportement nouveau a un test écrit **avant** le code
- [ ] Chaque test a été vu échouer, pour la bonne raison
- [ ] `uv run pytest -q` est vert, sans warning
- [ ] `uv run mypy src/` est vert
- [ ] Côté frontend : `npx tsc --noEmit` et `npm run test -- --run`
