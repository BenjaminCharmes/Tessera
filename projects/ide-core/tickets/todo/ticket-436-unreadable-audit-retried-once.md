---
id: ticket-436
title: "An unreadable security audit answer is asked again once before the run is blocked"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-14
---

# ticket-436 — Une réponse d'audit illisible est redemandée une fois

## Objectif

Qu'un défaut passager du modèle d'audit (réponse sans JSON valide) ne
bloque plus un ticket sain ni n'arrête une file entière, sans rien céder
sur le principe : l'audit échoue toujours fermé.

## Contexte

Le 2026-10-14 à 10:20 UTC, la file d'affût s'est arrêtée sur le ticket-053 :
« securite: BLOCK — Réponse de l'auditeur sécurité illisible (JSON
attendu) ». Le code n'était pas en cause : le modèle d'audit a rendu une
réponse que `extract_json(raw, required_key="verdict")` ne sait pas lire
(`SecurityAuditorService._parse_response`,
`services/security_auditor.py`). Deuxième cas depuis le 2026-10-07 ;
chacun coûte la file entière. ADR-039 : une réponse illisible bloque — il
ne s'agit pas d'y renoncer.

## Solution proposée

- Dans `audit`, si la première réponse est illisible, redemander **une**
  fois au même modèle, en ajoutant au message une consigne courte : « Ta
  réponse précédente n'était pas un JSON valide ; réponds uniquement par
  l'objet JSON demandé. »
- Si la seconde est lisible, elle fait foi ; sinon, blocage comme
  aujourd'hui, avec un motif qui dit que deux réponses ont été illisibles.
- Une exception du provider (indisponibilité) ne déclenche pas cette
  seconde tentative : c'est le repli d'ADR-046 qui s'en charge.
- Journal : `security_auditor_invalid_json` porte le numéro de tentative.

## Critères d'acceptation

- [ ] Un test vérifie qu'une première réponse illisible suivie d'une réponse
      `{"verdict": "PASS", …}` donne un audit PASS, en deux appels
- [ ] Un test vérifie que deux réponses illisibles donnent BLOCK, avec un
      motif qui mentionne les deux tentatives
- [ ] Un test vérifie qu'une exception du provider bloque sans seconde
      tentative (un seul appel)
- [ ] Un test vérifie qu'une première réponse lisible ne provoque qu'un
      appel

## Dépendances

Aucune.
