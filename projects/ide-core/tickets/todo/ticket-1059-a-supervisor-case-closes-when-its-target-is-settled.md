---
id: ticket-1059
title: "A supervisor case closes by itself once its ticket, rule or lesson is settled"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-26
---

# ticket-1059 — Un cas du superviseur se ferme seul quand sa cible est réglée

## Objectif

Le Bureau ne montre dans « À toi » que les cas du superviseur qui attendent
vraiment Benjamin.

## Contexte

Le 26/11, la colonne « À toi » affichait « 14 cas du superviseur à relire ».
Ils dataient du 10 au 20/11 et étaient tous réglés : douze règles et leçons
acceptées ou écartées à la main depuis, le ticket-1002 annulé, le ticket-985
fait. Benjamin ne savait pas où les relire, ni s'ils comptaient.

`cas_a_toi_ouverts` (`backend/src/tessera/services/supervision/superviseur_journal.py`)
ne ferme un cas que sur une ligne `resolu` du journal `memory/supervision.md`.
Aucun code n'en écrit : la liste ne peut que grossir. Elle sert à
`GET /supervision/recap` (`backend/src/tessera/routers/supervision_recap.py`)
et au compte `superviseur_a_toi` de `backend/src/tessera/routers/projects/listing.py`.

Une cible a trois formes :
- `ticket-XXX` : le ticket du projet supervisé ;
- `regle-<empreinte>` et `lecon-<empreinte>` : l'empreinte d'un bloc sous
  `## Proposées` de `memory/contraintes.md` ou `memory/lecons.md`, calculée par
  `cible_de` ; `blocs_proposes` rend les blocs encore proposés
  (`backend/src/tessera/services/supervision/superviseur_decision_blocs.py`).

## Solution proposée

Une fonction pure du domaine `supervision` reçoit les cas ouverts, les
identifiants des tickets réglés et le texte des deux fichiers de mémoire. Elle
rend les cas encore ouverts :
- un cas `ticket-XXX` dont le fichier est dans `tickets/done/` ou
  `tickets/cancelled/` est réglé ;
- un cas `regle-…` ou `lecon-…` dont l'empreinte n'est plus parmi les
  `blocs_proposes` de son fichier est réglé ;
- toute autre cible reste ouverte.

Le routeur du récap et le compte du listing passent par elle. Rien n'est écrit
dans le journal : c'est un filtre à la lecture.

## Critères d'acceptation

- [ ] Un test montre qu'un cas `ticket-XXX` disparaît quand le fichier du ticket
      est dans `tickets/done/`, et aussi dans `tickets/cancelled/`, et qu'il
      reste quand le fichier est dans `tickets/todo/`.
- [ ] Un test montre qu'un cas `regle-<empreinte>` reste tant que son bloc est
      sous `## Proposées` de `contraintes.md`, et disparaît quand le bloc a
      quitté la section. Même test pour `lecon-<empreinte>` et `lecons.md`.
- [ ] Un test montre qu'une cible d'une autre forme reste ouverte.
- [ ] Un test de `GET /api/v1/supervision/recap` montre qu'un cas réglé n'est
      plus dans `a_toi`, alors que la ligne `a_toi` reste dans `lignes`.
- [ ] Un test du listing des projets montre que `superviseur_a_toi` ne compte
      plus un cas réglé.
- [ ] Le diff n'écrit rien dans `memory/supervision.md` et ne modifie pas
      `ajouter_ligne`.

## Ce que ça ne fait pas

- Pas de bouton « Clore » dans le Bureau pour un cas que rien ne règle : à
  ticketer si des cas d'une autre forme restent bloqués.
- Ne change ni ce que le superviseur renvoie à l'humain, ni ses règles.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Le compte du listing lit deux fichiers de plus par appel : rester sur des
lectures simples, sans appel git.
