---
id: ticket-474
title: "The coder receives the reviewer's whole objection, and the log shows its first reason"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-16
---

# ticket-474 — Le codeur reçoit toute l'objection du reviewer

## Objectif

Au tour suivant, le codeur lit l'objection complète du reviewer, et le
journal montre sa première raison, pas seulement le mot du verdict.

## Contexte

make-your-call (Devinoo), 16/10, ticket-017 bloqué après 3 tours : tests
verts, validateur à 5 critères sur 6, reviewer à CHANGES_REQUESTED aux tours
2 et 3. Le journal ne disait que « CHANGES_REQUESTED tour 3: Reviewer :
CHANGES_REQUESTED ».

Le reviewer est prompté pour ouvrir sa réponse par le verdict seul sur sa
ligne (ADR-009). `_verdict_line` dans
`backend/src/tessera/services/pipeline_text.py` rend alors une raison vide.
Dans `backend/src/tessera/services/orchestrator.py`, le retour au codeur
devient `raw_verdict[:500]` : les 500 premiers caractères, coupés au milieu
d'une objection longue. Le journal tronque à 100 caractères et ne garde que
la première ligne, le verdict.

## Solution proposée

- Quand la ligne de verdict n'a pas de raison, la raison est le texte qui
  suit cette ligne, sans le verdict.
- Le retour au codeur garde ce texte jusqu'à 4 000 caractères (au lieu de
  500), avec la mention « […] tronqué » au-delà.
- La ligne du journal montre la première ligne non vide de la raison,
  pas le mot du verdict.

## Critères d'acceptation

- [ ] Un test vérifie qu'une réponse « CHANGES_REQUESTED » seule sur sa
      ligne puis trois paragraphes donne une raison qui contient le premier
      paragraphe et pas le mot CHANGES_REQUESTED
- [ ] Un test vérifie qu'une objection de 3 000 caractères arrive entière
      dans `run.review_feedback`
- [ ] Un test vérifie qu'une objection de 6 000 caractères est coupée à
      4 000 avec « tronqué »
- [ ] Un test vérifie que la ligne du journal contient la première ligne de
      la raison
