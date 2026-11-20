---
agent: codeur
created: 2026-11-20
depends_on: []
estimated_days: 1
id: ticket-1036
priority: medium
status: todo
title: A refused edition no longer drops the whole documentation batch
type: fix
---

# ticket-1036 — Une édition refusée ne fait plus tomber tout le lot de documentation

## Signalement

- Projet source : curio (20/11, tickets 108 et 109)
- La documentation par lot a été refusée deux fois sur la règle « jeton
  vérifiable » pour deux exemples entre guillemets, puis « abandonnée pour
  ticket-108 après 2 refus ». Le journal du projet compte 91 lignes
  « refusé : doc… ».

## Contexte

Vérifié le 20/11 dans le code :

- La règle n'a pas de défaut de comparaison : `documentation_preuve.py`
  aplatit et met en minuscules les deux côtés. Elle écarte **exprès** la
  documentation existante (« it is what carries the errors to correct »,
  ADR-057) : un exemple recopié du guide mais absent du diff et des tickets du
  lot se refuse, c'est voulu, et ce ticket n'y touche pas.
- Le défaut est ailleurs. `appliquer_editions`
  (`backend/src/tessera/services/documentation/documentation_editions.py`)
  lève `EditionRefusee` à la **première** édition que `controle.verifier`
  refuse : toutes les éditions du rôle tombent avec elle. Dans
  `documentation.py`, le tour de correction rappelle l'agent une fois ; s'il
  bute encore sur une édition, tout son travail est perdu une seconde fois, et
  le lot est abandonné au deuxième refus (ticket-940).

## Solution proposée

Au **tour de correction seulement** (le second appel d'`appliquer_editions`
dans `documentation.py`), une édition que le contrôle de preuve refuse
(`controle.verifier`) est écartée seule : les autres s'appliquent.

- `appliquer_editions` reçoit de quoi le dire (par exemple une liste
  `ecartees` que l'appelant fournit et qu'elle remplit du motif de chaque
  édition écartée) ; sans elle, son comportement ne change pas : la première
  édition refusée lève.
- Seuls les refus de `controle.verifier` s'écartent. Les autres refus
  (fichier hors documentation, création d'un fichier existant, ancre
  introuvable, amputation) lèvent comme aujourd'hui.
- Une édition écartée ne laisse aucune trace dans les fichiers écrits.
- Dans `documentation.py`, chaque motif écarté rejoint `refus` (donc le
  journal, sous sa forme actuelle « refusé : <rôle> : … ») et un événement
  `editions_refusees` est journalisé. Le lot n'est « tout refusé » que si
  aucun fichier n'a été écrit : la règle d'abandon du ticket-940 ne change
  pas.

## Critères d'acceptation

- [ ] Un test : deux éditions sur deux fichiers, la première refusée par la
      règle « jeton vérifiable », la seconde valide ; avec la liste fournie,
      la seconde est appliquée, la première ne l'est pas, et la liste porte
      son motif.
- [ ] Un test : les mêmes éditions sans la liste lèvent `EditionRefusee` et
      n'écrivent rien.
- [ ] Un test : avec la liste, une édition qui vise un fichier hors
      documentation lève toujours `EditionRefusee`.
- [ ] Un test du service (`backend/tests/test_documentation.py` ou un fichier
      voisin) : au premier tour une édition est refusée, au tour de correction
      l'agent rend une édition valide et une édition refusée ; le résultat
      porte le fichier écrit **et** le motif du refus, et le lot n'est pas
      compté comme tout refusé.
- [ ] `pytest` et `mypy` passent.

## Ce que ça ne fait pas

- Ne change aucune règle de `documentation_preuve.py` : la documentation
  existante reste hors de la matière vérifiable.
- N'ajoute pas de troisième tour.
- Ne change pas le premier tour : il reste tout ou rien, pour que l'agent
  reçoive le motif et corrige.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

`documentation_description.py` appelle aussi `controle.verifier` : il n'est
pas concerné, ne pas y toucher. `documentation_editions.py` fait 227 lignes :
rester sous le plafond de 300.
