---
agent: codeur
created: 2026-10-08
depends_on: []
estimated_days: 0.5
id: ticket-388
pr_number: null
priority: high
status: done
title: A subscription session limit pauses the queue and returns the ticket to todo,
  instead of blocking ticket after ticket
type: fix
---

# ticket-388 — Une limite de session met la file en pause au lieu de bloquer les tickets

## Objectif

Qu'atteindre la limite de session de l'abonnement n'abîme plus aucun ticket :
la file s'arrête proprement et dit quand reprendre.

## Contexte

Quand l'abonnement atteint sa limite, le CLI répond
« You've hit your session limit · resets 5pm (Europe/Paris) ». Le pipeline le
traite comme toute exception (`backend/src/tessera/services/pipeline_outcomes.py`) :
« INTERROMPU au tour N — ResultError: … », ticket en `blocked`, commit de
travail non approuvé. En file, le ticket suivant échoue de même.

Constaté plusieurs fois : portfolio le 2026-10-03 (ticket-008) et le
2026-10-04 (ticket-012), ide-core le 2026-10-08 à 09:42 (ticket-384) et
vigie le même jour à 13:36 (ticket-013). Chaque fois, il a fallu remettre les
tickets d'aplomb et relancer à la main après l'heure de reprise.

## Solution proposée

1. Reconnaître l'erreur de limite de session (le texte « hit your session
   limit », avec l'heure de reprise quand elle est présente).
2. Le ticket en cours repasse en `todo` (et non `blocked`) ; son travail reste
   commité comme non approuvé, sur sa branche.
3. La file s'arrête avant le ticket suivant et écrit
   `[<projet>] file interrompue : limite de session (reprise : <heure>)`
   dans `memory/pipeline-log.md`, et émet un événement portant la raison
   `session_limit` et l'heure de reprise.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_limite_de_session.py` vérifie qu'une erreur dont le message contient « You've hit your session limit · resets 5pm (Europe/Paris) » est reconnue, avec l'heure de reprise « 5pm (Europe/Paris) »
- [ ] Un test de `backend/tests/test_limite_de_session.py` vérifie qu'un run interrompu par cette erreur remet le ticket en `todo`, dossier et champ
- [ ] Un test de `backend/tests/test_limite_de_session.py` vérifie qu'une file de deux tickets s'arrête après le premier sur cette erreur, sans lancer le second, avec une ligne `file interrompue : limite de session` qui contient l'heure de reprise
- [ ] Un test de `backend/tests/test_limite_de_session.py` vérifie qu'une autre exception garde le comportement actuel (`blocked`)

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Un message d'erreur reformulé par le CLI ne serait plus reconnu : le cas
retomberait sur le comportement actuel, sans perte.

## Ce que ça ne fait pas

- Ne relance pas la file automatiquement à l'heure de reprise.
- Ne prévoit pas la limite à l'avance (le quota suivi par ADR-020 reste le
  garde-fou entre deux tickets).