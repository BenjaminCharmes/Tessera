---
agent: codeur
created: 2026-11-05
depends_on: []
estimated_days: 1
id: ticket-801
pr_number: null
priority: medium
status: done
title: A lessons module parses and checks the project lessons file
type: feat
---

# ticket-801 — Un module lit et contrôle le fichier de leçons d'un projet

## Objectif

Le format de `memory/lecons.md` et le contrôle d'une leçon existent en fonctions pures,
testées, avant que quoi que ce soit les appelle (ADR-074, cas d'origine : ticket-736).

## Contexte

Le fichier a deux sections, sur le modèle de `contraintes.md` (ADR-055) : `## Proposées`
(jamais injectée) et `## En vigueur` (la seule injectée). Une ligne = une leçon :
`- Quand <situation>, <action>. (source : ticket-NNN, AAAA-MM-JJ)`. La source est ajoutée
par le service, jamais écrite par le modèle.

## Interface à respecter

Nouveau fichier `backend/src/tessera/services/lecons.py` (300 lignes au plus) :

```python
PLAFOND_LECONS = 25          # leçons « En vigueur »
PLAFOND_OCTETS = 4096        # taille du fichier entier
LONGUEUR_MAX = 200           # caractères, source exclue

@dataclass(frozen=True)
class Lecons:
    en_vigueur: tuple[str, ...]
    proposees: tuple[str, ...]

def lire_lecons(memory_dir: Path) -> Lecons: ...        # fichier absent -> deux tuples vides
def refus_de_lecon(texte: str, preuve: str, existantes: Lecons, retour: str) -> str | None: ...
def ajouter_proposee(memory_dir: Path, texte: str, ticket_id: str, jour: date) -> None: ...
```

`refus_de_lecon` rend la raison du refus, ou `None` :

- **forme** : une ligne, commence par « Quand », contient « , », ne contient ni retour à la
  ligne, ni bloc de code, ni `##` ;
- **longueur** : plus de `LONGUEUR_MAX` caractères ;
- **preuve** : `preuve` (un passage que le modèle recopie, non stocké dans le fichier) fait
  au moins 20 caractères et se retrouve tel quel dans `retour` (le `review_feedback` du
  run) ;
- **doublon** : même texte une fois normalisé (casse, ponctuation, espaces), ou recouvrement
  de mots d'au moins 70 % avec une leçon `en_vigueur` ou `proposees` ;
- **vérification affaiblie** : le texte nomme un fichier de configuration des tests d'ADR-072
  (liste réutilisée, pas recopiée), `.github/workflows`, ou associe `skip`, `xfail`,
  `ignorer`, `désactiver`, `supprimer`, `baisser`, `--no-verify`, `continue-on-error`,
  `noqa` ou `type: ignore` à un test, au lint, au typage ou à la CI. Contrôle lexical : il
  attrape une erreur, pas une évasion ; la relecture humaine de `## Proposées` est la seconde
  barrière.

`ajouter_proposee` crée le fichier s'il manque, ajoute la source (`(source : ticket-NNN,
AAAA-MM-JJ)`) et n'écrit rien si le fichier atteindrait `PLAFOND_OCTETS` ou si
`en_vigueur` atteint `PLAFOND_LECONS` : un fichier plein se compacte à la main, jamais par
un agent.

## Critères d'acceptation

- [x] `lecons.py` porte la dataclasse, les trois fonctions et les trois constantes
      ci-dessus
- [x] `backend/tests/test_lecons.py` couvre : fichier absent ; lecture des deux sections ;
      chaque cause de refus (forme, longueur, preuve absente, doublon exact, doublon
      approché, fichier de configuration nommé, `skip` associé à un test) ; une leçon valide
      acceptée ; ajout qui crée le fichier et pose la source ; ajout refusé au plafond
      d'octets et au plafond de leçons
- [x] Un test écrit la leçon du ticket-736 (« Quand une méthode s'ajoute à
      `GitWorkspaceService`, chercher les doubles de test qui la redéfinissent… ») avec sa
      preuve et vérifie qu'elle passe
- [x] Aucun appel à un provider, aucun import de `orchestrator`

## Ce que ça ne fait pas

N'injecte rien dans un prompt (ticket-802), ne produit aucune leçon (ticket-803), ne garde
rien (ticket-804).

## Dépendances

Aucune.
