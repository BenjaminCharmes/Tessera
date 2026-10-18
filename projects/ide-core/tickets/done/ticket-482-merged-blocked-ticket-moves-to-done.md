---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.5
id: ticket-482
plan: true
pr_number: 528
priority: medium
status: done
title: A blocked ticket whose branch was merged by hand is moved to done
type: fix
---

# ticket-482 — Un ticket bloqué livré à la main passe en `done`

## Objectif

Quand la PR de la branche d'un ticket `blocked` est mergée (livraison à la
main après vérification), le ticket passe en `done` sans geste manuel.

## Contexte

devinoo, 16/10 : le ticket-017, bloqué par le pipeline puis livré à la main
(PR #35 mergée), est resté dans `tickets/blocked/` sur main. La session l'a
déplacé à la main. Même geste côté ide-core pour les tickets 446, 450 et 458.

## Solution proposée

Au réalignement de la base (tickets 403, 457) ou au départ d'une file : pour
chaque ticket `blocked`, chercher une PR mergée dont la branche commence par
`<ticket-id>-`. Si elle existe, déplacer le ticket dans `done/`, passer son
`status` à `done`, renseigner `pr_number`, et inclure ce déplacement dans le
commit de tenue de livres du run suivant. Journaliser « ticket-N rangé en
done : PR #M mergée ».

## Critères d'acceptation

- [ ] Un test vérifie qu'un ticket `blocked` dont la PR de branche est
      mergée passe dans `done/` avec `status: done` et son `pr_number`
- [ ] Un test vérifie qu'un ticket `blocked` sans PR mergée reste bloqué
- [ ] Un test vérifie la ligne de journal