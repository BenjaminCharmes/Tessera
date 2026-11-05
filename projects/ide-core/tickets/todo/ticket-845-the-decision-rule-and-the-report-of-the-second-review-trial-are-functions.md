---
id: ticket-845
title: "The decision rule and the report of the second-review trial are functions"
type: chore
status: todo
priority: low
agent: codeur
created: 2026-11-05
depends_on: [ticket-841, ticket-843]
estimated_days: 1
pr_number: null
---

# ticket-845 — La règle de décision et le rapport de l'essai sont des fonctions

## Objectif

Appliquer la règle d'ADR-079 (spec §4 et §5) aux résultats et à la relecture, en fonctions
pures, sur le modèle de `scripts/mesure_verdict.py` (ticket-605).

## Interface à respecter

Nouveau fichier `scripts/seconde_revue_decision.py` (300 lignes au plus) :

```python
@dataclass(frozen=True)
class Mesures:
    valide: bool                       # rejeu valide (spec §4, point 4)
    defauts_en_plus: int
    defauts_en_plus_sensibles: int
    faux_positifs_en_plus: int
    faux_positifs_en_plus_sensibles: int
    duree_ajoutee_ms: int              # durée moyenne d'une revue de C
    cout_c_moyen: float
    cout_b_moyen: float

@dataclass(frozen=True)
class Verdict:
    decision: Literal["adopter", "reserver", "abandonner", "non concluant"]
    motif: str

def decision(m: Mesures) -> Verdict: ...
def mesures_depuis(
    corpus: Corpus, resultats: Sequence[Resultat], relecture: Sequence[Jugement]
) -> Mesures: ...
def rapport(corpus: Corpus, resultats: Sequence[Resultat], relecture: Sequence[Jugement]) -> str: ...
```

`Jugement` : `id`, `bras`, `rang` (position de la remarque), `jugement` parmi `confirme`,
`autre_defaut`, `infonde` ; `lire_relecture(chemin)` lit `relecture.json`.

Règle, dans l'ordre : `valide` faux → `non concluant` ; sinon `adopter` si défauts en plus ≥ 3,
faux positifs en plus ≤ 2, durée ajoutée ≤ 300 000 ms et `cout_c_moyen ≤ cout_b_moyen` ; sinon
`reserver` si défauts en plus sensibles ≥ 2 et faux positifs en plus sensibles ≤ 1 ; sinon
`abandonner`.

`mesures_depuis` : un défaut en plus = une entrée `defaut` où C lève et B non, avec au moins
une remarque de C jugée `confirme` ou `autre_defaut` ; un faux positif en plus = une entrée
`sain` où C lève et B non, avec une remarque de C jugée `infonde`. Les entrées `hors_fenetre`,
`indisponible` et `hors_schema` de C sont exclues des comptes. `valide` : B approuve au moins
80 % du corpus **et** les exclues de C sont sous 25 %. `rapport` rend le Markdown de
`docs/essais/seconde-revue.md` : tableau par bras, comptes, coût, durée, et un bloc de
conclusion entre `<!-- seconde-revue-conclusion:debut -->` et `<!-- seconde-revue-conclusion:fin -->`.

## Critères d'acceptation

- [ ] `scripts/seconde_revue_decision.py` porte les types et les fonctions ci-dessus
- [ ] `backend/tests/test_seconde_revue_decision.py` couvre `decision` : une branche par test
      (`non concluant`, `adopter`, `reserver`, `abandonner`) et les bornes : 3 défauts en plus
      adopte, 2 ne le fait pas ; 2 faux positifs en plus adopte, 3 non ; durée à 300 000 ms
      adopte, 300 001 non ; coût de C supérieur à celui de B refuse `adopter` et retombe sur
      `reserver` quand les comptes sensibles le permettent
- [ ] Le même fichier couvre `mesures_depuis` : un `infonde` ne compte pas comme défaut ;
      un défaut que B lève aussi ne compte pas ; une entrée `hors_fenetre` est exclue ; 79 %
      d'approbations de B rendent `valide` faux, 80 % vrai ; 25 % d'exclues de C rendent
      `valide` faux
- [ ] Un test de `rapport` vérifie la présence du bloc balisé et que sa décision est celle de
      `decision(mesures_depuis(...))`

## Ce que ça ne fait pas

Ne lit aucun fichier de résultats réel et ne décide rien : la décision est une recommandation,
l'ADR d'adoption appartient à un humain.

## Dépendances

tickets 805 et 807.
