---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 1
id: ticket-914
plan: true
pr_number: 1037
priority: medium
status: done
title: The supervisor decides each proposed block once, not again whenever another
  block appears
type: fix
---

# ticket-914 — Le superviseur décide chaque bloc proposé une fois, pas à chaque nouveau bloc

## Objectif

Qu'une règle ou une leçon proposée ne soit décidée, et renvoyée « À toi »,
qu'une seule fois, même quand d'autres blocs arrivent ensuite sous
`## Proposées`.

## Contexte

Le 10/11, les PR #1013 (11:37) et #1018 (13:24) portaient exactement la même
ligne : `a_toi | regle-d2a98cda`. Entre les deux, une leçon du ticket-906 était
arrivée sous `## Proposées` de `memory/lecons.md`.

Deux causes s'additionnent :

- `superviseur_collecte.py` (`_candidats_decision`) bâtit **un seul**
  candidat `DECIDER` par projet, dont la clé d'idempotence (`Candidat.cle`,
  `superviseur_boucle_ports.py`) est l'empreinte de **tous** les blocs
  proposés, règles et leçons ensemble. Un bloc ajouté change la clé : tous les
  blocs sont redécidés, appel de modèle compris, y compris ceux déjà renvoyés
  « À toi ». `superviseur_cles.json` porte ainsi 17 clés `decider` pour
  ide-core.
- `intervention_a_toi.py` (`_nouvelles`) ne double pas une ligne déjà dans le
  journal, mais lit le journal du worktree tiré de `origin/<base>` : la ligne
  d'une PR « À toi » encore ouverte n'y est pas.

## Solution proposée

- La décision se fait bloc par bloc du point de vue de l'idempotence : un bloc
  déjà décidé (même genre, même cible, même texte) n'est plus soumis au
  modèle. Soit un candidat par bloc, soit un candidat dont `executer` ne passe
  à `decider` que les blocs dont l'empreinte n'est pas encore marquée — au
  plan de trancher, en gardant `EtatIdempotence` comme seule mémoire.
- Un bloc dont le texte change redevient à décider (nouvelle empreinte).
- Le comportement face à un bloc nouveau reste celui d'aujourd'hui.

## Critères d'acceptation

- [ ] Un test vérifie, avec des doubles, qu'après une passe qui a décidé un
      bloc A, une seconde passe où un bloc B est apparu ne soumet que B à la
      décision.
- [ ] Un test vérifie qu'un bloc A dont le texte a changé est soumis de
      nouveau.
- [ ] Un test vérifie qu'un bloc renvoyé « À toi » à la première passe ne
      produit pas de seconde intervention « À toi » quand un autre bloc
      apparaît.
- [ ] Le diff ne modifie ni `intervention.py` ni les gardes de
      `superviseur_actions.py`.

## Ce que ça ne fait pas

- Ne lit pas les PR ouvertes sur GitHub : l'idempotence reste locale.
- Ne nettoie pas les anciennes clés de `superviseur_cles.json`.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

`decider` peut juger un bloc à la lumière des autres (deux règles
contradictoires) : le plan dit si la décision par bloc perd cette vue, et
si oui garde l'ensemble des blocs en contexte en ne demandant un verdict que
pour les nouveaux.