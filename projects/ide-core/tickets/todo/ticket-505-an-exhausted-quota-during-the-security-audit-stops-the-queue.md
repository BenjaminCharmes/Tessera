---
id: ticket-505
title: "An exhausted quota during the security audit stops the queue as a quota stop, not as a blocked ticket"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-19
---

# ticket-505 — Un quota épuisé pendant l'audit est un arrêt de quota, pas un ticket bloqué

## Objectif

Quand l'audit sécurité échoue parce que le quota d'abonnement est épuisé, le
run s'arrête comme le prévoit le ticket-498 (« quota épuisé — reprise vers
HH:MM », ticket remis en `todo`, file interrompue pour quota), au lieu de
rendre `BLOCK` et de compter le ticket comme refusé.

## Contexte

18/10 à 20:25 UTC, file ide-core, ticket-492 : codeur et testeur verts, puis
`securite: BLOCK — Audit sécurité indisponible : Claude Code returned an error
result: You've hit your limit…`, et « file interrompue : ticket-492 non
approuvé ». Le travail a été commité en « unapproved work ».

`SecurityAuditorService.audit` (`security_auditor.py`) attrape toute exception
et rend `_blocked("Audit sécurité indisponible : …")` (ADR-039, échec fermé).
Le ticket-498 reconnaît un quota épuisé sur les appels d'agents
(`quota_exhaustion.is_quota_exhausted`), mais l'audit ne lui transmet jamais
l'exception : elle est déjà convertie en verdict.

## Solution proposée

1. Dans `audit`, une exception que `is_quota_exhausted` reconnaît (texte « You've
   hit your limit », « usage limit », snapshot `rejected`) est relevée telle
   quelle au lieu d'être convertie en `BLOCK`. Même chose dans
   `_audit_diff_only`.
2. L'orchestrateur la traite par le chemin du ticket-498 : journal « quota
   épuisé », ticket en `todo`, file interrompue pour quota.
3. Toute autre exception garde l'échec fermé actuel (`BLOCK`, ADR-039).
4. Même règle pour le validateur s'il convertit lui aussi les exceptions en
   verdict.

## Critères d'acceptation

- [ ] Un test vérifie qu'une exception « You've hit your limit » pendant
      l'audit n'est pas convertie en `BLOCK` mais relevée
- [ ] Un test vérifie qu'une autre exception de l'audit rend toujours `BLOCK`
- [ ] Un test de l'orchestrateur vérifie qu'un quota épuisé pendant l'audit
      écrit « quota épuisé » au journal et interrompt la file pour quota
- [ ] Un test vérifie le même comportement pour le validateur
