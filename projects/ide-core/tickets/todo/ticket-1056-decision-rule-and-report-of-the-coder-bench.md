---
id: ticket-1056
title: "Decision rule and report of the coder bench"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: [ticket-1055]
estimated_days: 1
created: 2026-11-26
---

# ticket-1056 — Règle de décision et rapport du banc du codeur

## Objectif

Des fonctions pures qui lisent le corpus et les résultats, appliquent la règle fixée par ADR-095
et écrivent un rapport qu'un humain lit.

## Contexte

Conception §6. Modèle : `scripts/seconde_revue_decision.py` (ticket-845), dont on garde la forme : constantes
entières en tête de fichier, `decision`, `mesures_depuis`, `rapport`, bloc de conclusion balisé.

## Solution proposée

`scripts/banc_codeur_decision.py`. Rapport : `docs/essais/banc-codeur.md`.

## Critères d'acceptation

- [ ] Les seuils de la conception §6 sont des constantes nommées : 14 reproductions sur 20, 4 exclues au plus,
      3 entrées d'écart, 40 % de coût en moins, 2 × la durée, divergence A/A2 sur 3 entrées de 5.
- [ ] `decision` applique la règle dans l'ordre : non concluant, meilleur, moins cher, garder A ;
      un test par branche, et un test de l'égalité entre deux bras.
- [ ] Une entrée `echec_env` sort de tous les bras avant tout calcul ; une cellule `indisponible` compte comme exclue.
- [ ] `T1`, `V` et `C` se calculent par bras sur les mêmes entrées (appariées) ; `tests_reference_verts` n'entre
      dans aucune décision, il figure au rapport.
- [ ] Le rapport donne par bras : cellules, `T1`, `V`, tours moyens, coût moyen et maximum, jetons, durée
      moyenne et maximum ; puis la recommandation dans un bloc balisé, avec la phrase que l'ADR qui décide
      appartient à un humain.
- [ ] Une relance du calcul sur le même JSONL rend le même rapport, octet pour octet.

## Ce que ça ne fait pas

- Ne modifie aucun résultat et ne décide pas à la place de l'humain.

## Dépendances

ticket-1055 (format de ligne).

## Estimation

Une journée.

## Risques

Le seuil de bruit A/A2 repose sur 5 entrées : il ne détecte qu'un bruit grossier, et le rapport le dit.
