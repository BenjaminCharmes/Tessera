---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 0.5
id: ticket-268
pr_number: 136
priority: critical
status: done
title: Validator matches verdicts to criteria by number, not by exact text
type: fix
---

# ticket-268 — Le validateur rattache ses verdicts par numéro de critère

## Objectif

Qu'un critère jugé par le validateur ne soit plus compté « non jugé » parce que
le LLM l'a recopié avec une virgule de différence.

## Contexte

Constaté le 2026-09-30 sur le ticket-265 : deux tours refusés, avec un
feedback « Tous les critères d'acceptation sont satisfaits » et un verdict
`CHANGES_REQUESTED`. Le détail de `validation_done` :

```
True  | Un test montre que `merge_pull_request` envoie ...
True  | Un test montre qu'un projet sans `merge_method` ...
False | Un test montre qu'un projet déclarant `"merge_method": "merge"` ... | non jugé par le validateur
True  | Un test montre qu'une valeur inconnue retombe sur `squash`.
```

`ValidatorService` (`services/validator.py`) rapproche chaque critère envoyé
de la réponse du LLM **par texte exact**, seulement passé en minuscules et
débarrassé de la case à cocher (`_normalize`). Un LLM qui réécrit des
guillemets, des backticks ou un espace produit un texte différent : le critère
est ajouté en `passed: false`, et ADR-039 fait refuser le run. Le critère
fautif contenait justement des guillemets dans des backticks.

## Solution proposée

- Le prompt du validateur (`agents/prompts/validateur.md`) numérote les
  critères envoyés et exige un champ `index` (entier, à partir de 1) dans
  chaque entrée de `criteria`.
- Le rapprochement se fait par `index` d'abord ; à défaut d'`index` valide,
  par texte normalisé **plus tolérant** : sans backticks, guillemets droits ou
  typographiques, ponctuation finale ni espaces multiples.
- Un critère qu'aucune des deux voies ne retrouve reste `passed: false` avec
  « non jugé par le validateur » (ADR-039 inchangé).
- Le `feedback` renvoyé ne peut plus contredire le verdict : si un critère est
  « non jugé », le feedback le dit en tête.

## Critères d'acceptation

- [ ] Un test montre qu'une réponse portant `index: 3` est rattachée au
      troisième critère même si son texte diffère du critère envoyé.
- [ ] Un test montre qu'une réponse sans `index`, dont le texte ne diffère du
      critère que par des backticks et des guillemets, est rattachée à ce
      critère.
- [ ] Un test montre qu'un critère absent de la réponse reste `passed: false`
      avec la note « non jugé par le validateur ».
- [ ] Un test montre que le feedback d'une validation avec un critère non jugé
      commence par une phrase qui le signale.
- [ ] `agents/prompts/validateur.md` décrit le champ `index` dans le format de
      réponse.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Backend et prompt.

## Risques

Le prompt du validateur part dans chaque validation de tous les projets :
changement minimal, format de réponse rétrocompatible (le texte reste lu).