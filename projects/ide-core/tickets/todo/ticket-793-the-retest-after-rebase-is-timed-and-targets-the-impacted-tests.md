---
id: ticket-793
title: "The retest after rebase runs only the backend tests the rebase can affect"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-793 — Le retest après rebase ne lance que les tests backend que le rebase peut toucher

## Objectif

La livraison d'un ticket backend ne passe plus 12 à 17 minutes à relancer toute la suite après
le rebase, sans perdre ce que ce retest protège.

## Contexte

Mesuré le 04/11 sur la file ide-core (étape « tests relancés après rebase » de
`livraison_done`) : 13,2 min (752), 12,3 (754), 12,1 (751), 14,3 (760), 17,0 (766) ; 3 min pour
les tickets frontend. Un ticket dure 30 à 35 minutes : ce retest en est près de la moitié.
Chronométré à la main le même jour : pytest seul 14 min 36 (4 824 tests, 8 processus, deux files
en parallèle), mypy natif 2 min 31 et mypy linux 1 min 23 en parallèle de pytest.

`retest_apres_rebase.py` (ticket-568) relance la commande du testeur quand le rebase ramène des
commits de la base ; le ticket-584 l'évite quand base et branche ne touchent pas la même chaîne.
Dans une file, chaque ticket backend vient d'être mergé : le suivant partage toujours la chaîne
backend et relance toute la suite.

**Fait à la main** (agents interdits d'écriture sur le script de `test_command`) :
`scripts/verifier.py` accepte `--impact <ref>`. pytest ne lance alors que les fichiers de test
que le diff `<ref>..HEAD` peut toucher (tests modifiés, tests qui importent un module modifié ou
un module qui l'importe) ; toute la suite si le diff est illisible ou touche une configuration,
un utilitaire de test ou `scripts/`. Mesuré sur les tickets du jour : 1 à 69 fichiers sur 367,
227 pour un module central. Le script imprime aussi la durée de chaque étape.

## Solution proposée

- `retest_apres_rebase.py` relève, **avant** le rebase, le SHA de la base sous la branche
  (`merge-base` avec la base).
- Quand le projet porte `scripts/verifier.py` (`_porte_un_verifier`), le retest lance la commande
  du testeur suivie de `--impact <sha>`. Sinon, la commande reste inchangée.
- Si le SHA ne se lit pas, la commande part sans l'option (suite complète, ADR-039).
- La commande du testeur pendant le run ne change pas.

## Critères d'acceptation

- [ ] Un test de `retest_apres_rebase.py` vérifie, avec des doubles, que le retest d'un projet
      qui porte un verifier lance la commande suivie de `--impact` et du SHA relevé avant le
      rebase
- [ ] Un test vérifie que, pour un projet sans verifier, la commande du retest est inchangée
- [ ] Un test vérifie que, si le SHA ne se lit pas, la commande part sans `--impact`

## Ce que ça ne fait pas

La CI reste la porte complète : elle rejoue toute la suite sur la PR.
