---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 0.5
id: ticket-516
pr_number: null
priority: high
status: done
title: The CI watch resumed after a restart finds the pipeline's open pull requests
  on GitHub, not in the local ticket files
type: fix
---

# ticket-516 — La reprise de surveillance trouve les PR ouvertes sur GitHub

## Objectif
Qu'après un redémarrage, toute PR ouverte par le pipeline et encore en
attente de CI soit de nouveau surveillée et mergée, quel que soit l'état des
fiches dans l'arbre local.

## Contexte
Le ticket-510 (`backend/src/tessera/services/reprise_surveillance.py`) cherche
les tickets `in-review` qui portent un `pr_number` dans l'arbre de travail du
projet. Or, après la phase 1 de livraison, ce statut et ce numéro ne sont
écrits que sur la **branche du ticket**, dans la PR elle-même. Sur la base,
la fiche reste en `todo` jusqu'au merge.

Le 19/10 à 13:45 UTC, premier redémarrage avec le 510 actif : la PR #41 de
Kadoomi (ticket-034, ouverte à 13:39 et confiée au CIWatcher) était OPEN et
CLEAN. Elle n'a pas été reprise, car sa fiche était `todo` sur `main`. La session
Kadoomi l'a mergée à la main.

## Solution proposée
Pour chaque projet en autonomie `merge` avec un `github_remote`, lister les PR
**ouvertes** du dépôt dont la branche de tête suit le motif des branches de
ticket (`ticket-NNN-…`) et dont la base est la `base_branch` du projet. Chacune
est confiée à `CIWatcher.surveiller`, avec le ticket déduit du nom de branche.
Les règles d'exclusion du 510 restent : les PR de résolution de conflit
(ADR-033) ne se mergent jamais seules. La source « fiches `in-review` locales »
peut rester comme complément, sans doublon.

## Critères d'acceptation
- [ ] Dans `reprise_surveillance.py`, une PR ouverte dont la branche est `ticket-034-…` est reprise même quand la fiche locale du ticket est en `todo` (un test le vérifie avec un faux client GitHub)
- [ ] Un test vérifie qu'une PR dont la branche ne suit pas le motif `ticket-NNN-` n'est pas reprise
- [ ] Un test vérifie qu'une PR vers une autre base que la `base_branch` du projet n'est pas reprise
- [ ] Un test vérifie qu'une même PR trouvée par les deux sources n'est confiée qu'une fois au CIWatcher
- [ ] Les tests existants de `test_reprise_surveillance.py` passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
Une PR ouverte à la main sur une branche `ticket-NNN-` serait aussi mergée à
CI verte : c'est le comportement attendu en autonomie `merge`, à noter dans
la documentation.