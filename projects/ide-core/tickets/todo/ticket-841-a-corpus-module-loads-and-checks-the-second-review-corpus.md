---
id: ticket-841
title: "A corpus module loads and checks the second-review trial corpus"
type: chore
status: todo
priority: low
agent: codeur
created: 2026-11-05
depends_on: []
estimated_days: 1
pr_number: null
---

# ticket-841 — Un module charge et contrôle le corpus de l'essai de seconde revue

## Objectif

Le format du corpus et ses contrôles existent en fonctions pures, testées, avant qu'on
étiquette quoi que ce soit (ADR-079, `docs/superpowers/specs/2026-11-05-seconde-revue-design.md`
§2).

## Interface à respecter

Nouveau fichier `scripts/seconde_revue_corpus.py` (300 lignes au plus). Hors de
`backend/src` : le produit ne l'importe jamais.

```python
CHEMINS_SENSIBLES: tuple[str, ...]   # motifs fnmatch de la spec §2, « diffs sensibles »

class CorpusInvalide(ValueError): ...

@dataclass(frozen=True)
class Entree:
    id: str
    ticket: str                      # « ticket-733 »
    sha: str                         # commit de squash ; diff = sha^..sha
    classe: Literal["defaut", "sain"]
    preuve: str                      # vide pour « sain »
    fichiers_defaut: tuple[str, ...] # vide pour « sain »
    defaut: str                      # vide pour « sain »
    sensible: bool

@dataclass(frozen=True)
class Corpus:
    entrees: tuple[Entree, ...]
    gel_sha256: str

def est_sensible(fichiers: Iterable[str]) -> bool: ...
def somme_gel(entrees: Iterable[Entree]) -> str: ...        # indépendante de l'ordre
def charger_corpus(chemin: Path) -> Corpus: ...              # CorpusInvalide si hors forme
def verifier_taille(corpus: Corpus) -> list[str]: ...        # raisons ; [] si conforme
def shas_manquants(corpus: Corpus, depot: Path) -> list[str]: ...   # git cat-file, lecture seule
def diff_de(entree: Entree, depot: Path) -> str: ...         # git diff sha^..sha, lecture seule
```

`charger_corpus` refuse : champ absent ou de mauvais type, `classe` hors énumération, `id` ou
`sha` en double, un `defaut` sans `preuve`, `fichiers_defaut` ou `defaut`, un `sain` qui en
porte, et un `gel_sha256` qui ne correspond pas à `somme_gel`. `verifier_taille` rend une
raison par seuil manqué : moins de 10 `defaut`, moins de 10 `sain`, moins de 4 `defaut`
sensibles.

## Critères d'acceptation

- [ ] `scripts/seconde_revue_corpus.py` porte les types et les six fonctions ci-dessus
- [ ] `backend/tests/test_seconde_revue_corpus.py` couvre : `est_sensible` vrai pour
      `backend/src/tessera/services/providers/git_guard.py` et faux pour
      `frontend/src/App.tsx` ; `somme_gel` stable quand l'ordre change et différente quand une
      entrée change ; `charger_corpus` sur un fichier valide, puis une cause de refus par
      test (champ absent, classe inconnue, `id` en double, `defaut` sans preuve, `sain` avec
      `fichiers_defaut`, somme de gel fausse) ; `verifier_taille` sur un corpus trop petit et
      sur un corpus conforme ; `shas_manquants` et `diff_de` sur un dépôt temporaire créé par
      le test avec deux commits
- [ ] Les appels git sont en lecture seule (`cat-file`, `diff`) ; aucun import de `tessera`

## Ce que ça ne fait pas

N'écrit aucune entrée de corpus (ticket-842), n'appelle aucun modèle (ticket-844).

## Dépendances

Aucune.
