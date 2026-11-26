---
id: ticket-1058
title: "Run the coder bench trial, read it and conclude"
type: chore
status: todo
priority: medium
agent: codeur
depends_on: [ticket-1057]
estimated_days: 2
created: 2026-11-26
---

# ticket-1058 — Lancer l'essai du banc du codeur, le lire et conclure

## Objectif

Une recommandation chiffrée sur le couple modèle + prompt du codeur, lue par un humain.

## Contexte

ADR-095. Corpus de 16 à 20 entrées (taille proposée par `pilote.md`), trois bras A, M, P, plus A rejoué sur 5
entrées (A2) : 65 cellules au plus. Plafond **100 $** d'estimation SDK, que l'humain confirme au lancement.
Le texte de la variante P est validé par l'humain avant le gel.

## Solution proposée

Geler le corpus et les bras (somme dans `corpus.json` et `bras.json`), lancer
`scripts/banc_codeur.py --budget-usd 100`, relancer après toute coupure (reprise), puis générer le rapport.

## Critères d'acceptation

- [ ] `corpus.json` et `bras.json` sont gelés (`gel_sha256`) et commités **avant** la première ligne de
      `resultats.jsonl`, et la variante P est celle que l'humain a validée.
- [ ] `resultats.jsonl` porte une ligne par cellule jouée, chacune avec le `gel_sha256` du corpus ; la somme
      de `cout_codeur_usd` et `cout_controles_usd` ne dépasse pas 100 $.
- [ ] `docs/essais/banc-codeur.md` est généré par `scripts/banc_codeur_decision.py` et porte le bloc de
      conclusion balisé : comptes, `T1`, `V`, coût et durée par bras, recommandation.
- [ ] Un humain a lu les cellules refusées au tour 1 de A (au moins la remarque du reviewer et l'état des
      tests) et l'a noté au rapport.
- [ ] Le rapport dit si l'essai est concluant (A reproduit au moins 14 entrées sur 20, bruit A/A2 acceptable)
      et, sinon, pourquoi il ne l'est pas.
- [ ] Ni `backend/src/`, ni `agents.json`, ni `agents/prompts/` ne sont modifiés : une adoption est une autre
      ADR et un autre ticket.

## Ce que ça ne fait pas

- N'adopte aucun modèle ni prompt.
- Ne change ni le reviewer, ni le validateur, ni le testeur.

## Dépendances

ticket-1057.

## Estimation

Deux jours, dont une partie en attente de tests.

## Risques

Un quota entamé en cours d'essai : la reprise par JSONL permet de couper et de relancer sans perte.
