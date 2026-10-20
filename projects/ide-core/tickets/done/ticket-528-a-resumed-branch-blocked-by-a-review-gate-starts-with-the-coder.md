---
agent: codeur
created: 2026-10-20
depends_on: []
estimated_days: 0.5
id: ticket-528
pr_number: 590
priority: high
status: done
title: A resumed branch whose last run was refused by the security audit or the validator
  starts again with the coder
type: fix
---

# ticket-528 — Une branche reprise après un refus d'une porte repart par le codeur

## Objectif
Qu'un ticket bloqué par l'audit sécurité ou par le validateur ne soit pas
renvoyé tel quel aux mêmes portes à sa relance, ce qui le bloquerait de
nouveau à coup sûr.

## Contexte
À la reprise d'une branche qui porte du travail (`verifier_travail_repris`,
`backend/src/tessera/services/pipeline_reprise.py`), des tests verts font sauter
le codeur (« branche reprise (N commit(s)) — tests green, codeur sauté ») et le
run passe directement à l'audit puis à la revue. C'est juste après une coupure
(redémarrage, quota) : le travail était bon, il n'a pas été jugé.

C'est faux après un REFUS. Le 19/10 à 22:06 UTC, l'audit sécurité a bloqué
ide-core ticket-522 (traversée de chemin CRITICAL). À la relance, la branche
avait des tests verts : codeur sauté, même code renvoyé à l'audit, nouveau
BLOCK à 22:20. Le correctif a dû être écrit à la main.

## Solution proposée
Le dernier run du ticket s'est terminé sur un refus d'une porte (`securite:
BLOCK`, validateur ou reviewer `CHANGES_REQUESTED` au dernier tour, ou
`BLOCKED après N tour(s)`) : la reprise commence par un tour de codeur, avec
dans son contexte le motif de ce refus (déjà en base ou dans le journal). Une
reprise après une coupure garde le comportement actuel.

## Critères d'acceptation
- [ ] Un test vérifie qu'une reprise dont le dernier run s'est terminé sur un `securite: BLOCK` lance le codeur même avec des tests verts
- [ ] Un test vérifie que le motif du refus précédent figure dans le contexte de ce tour de codeur
- [ ] Un test vérifie qu'une reprise après une coupure (run interrompu, sans verdict) saute toujours le codeur quand les tests sont verts
- [ ] La ligne de journal de la reprise dit pourquoi le codeur est lancé (`… — refus précédent : <porte>, codeur en premier`)
- [ ] Les tests existants de la reprise passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
Ne pas relancer le codeur sur un ticket approuvé mais non livré (fiche `done`) :
celui-là n'a rien à corriger.