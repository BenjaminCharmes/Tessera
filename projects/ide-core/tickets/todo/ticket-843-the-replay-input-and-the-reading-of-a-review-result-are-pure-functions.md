---
id: ticket-843
title: "The replay input and the reading of a review result are pure functions"
type: chore
status: todo
priority: low
agent: codeur
created: 2026-11-05
depends_on: [ticket-841]
estimated_days: 1
pr_number: null
---

# ticket-843 — L'entrée du rejeu et la lecture d'un résultat sont des fonctions pures

## Objectif

Ce qu'on envoie au modèle et ce qu'on consigne se calculent sans provider, pour que le rejeu
(ticket-844) n'ait plus qu'à les brancher (ADR-079, spec §3 et §4).

## Interface à respecter

Nouveau fichier `scripts/seconde_revue_lecture.py` (300 lignes au plus). Il peut importer
`tessera.services.reviewer_schema` et `tessera.services.verdict_reviewer` : ce sont les
fonctions que le pipeline utilise, pas une copie.

```python
Etat = Literal["ok", "indisponible", "hors_fenetre", "hors_schema"]

def corps_du_ticket(ticket: str, racine_tickets: Path) -> str: ...
    # cherche tickets/{done,in-review,in-progress,todo,blocked}/<ticket>-*.md ; ValueError si absent

def composer_entree(corps_ticket: str, diff: str) -> str: ...
    # le ticket, puis « ## Code produit par le codeur » et le diff ; ni test, ni audit

def leve(structured: dict[str, Any] | None, seuil: int) -> bool: ...
    # True quand lire_verdict refuse : une remarque au moins au seuil, ou sortie illisible

def remarques_au_seuil(structured: dict[str, Any] | None, seuil: int) -> tuple[dict[str, Any], ...]: ...

def designe_le_defaut(remarque: dict[str, Any], fichiers_defaut: Sequence[str]) -> bool: ...
    # un fichier de fichiers_defaut apparaît dans `location` ou `text` (casse et séparateurs
    # normalisés) ; propose un appariement, ne tranche pas

@dataclass(frozen=True)
class Resultat:
    id: str; bras: Literal["B", "C"]; modele: str; gel_sha256: str
    etat: Etat; leve: bool | None
    remarques: tuple[dict[str, Any], ...]
    cout_usd: float; duree_ms: int

def vers_ligne(r: Resultat) -> str: ...          # une ligne JSON, sans retour à la ligne
def lire_resultats(chemin: Path) -> list[Resultat]: ...   # fichier absent -> []
```

## Critères d'acceptation

- [ ] `scripts/seconde_revue_lecture.py` porte les fonctions et le type ci-dessus
- [ ] `backend/tests/test_seconde_revue_lecture.py` couvre : `corps_du_ticket` trouvé dans
      `done` puis absent (`ValueError`) ; `composer_entree` contient le ticket et le diff et
      aucune section de test ni d'audit ; `leve` faux pour un `APPROVED`, vrai pour un
      `CHANGES_REQUESTED` avec une remarque au seuil, faux pour un `CHANGES_REQUESTED` dont
      toutes les remarques sont sous le seuil, vrai pour `None` et pour une sortie hors schéma ;
      `designe_le_defaut` avec un chemin Windows (`\`) et un chemin POSIX ; un aller-retour
      `vers_ligne` / `lire_resultats` ; fichier absent
- [ ] `leve` et `remarques_au_seuil` délèguent à `lire_verdict` : un test change le seuil et
      vérifie que les deux suivent

## Ce que ça ne fait pas

N'appelle aucun provider, n'écrit aucun fichier (`lire_resultats` lit seulement).

## Dépendances

ticket-841 (le type `Entree` sert aux signatures).
