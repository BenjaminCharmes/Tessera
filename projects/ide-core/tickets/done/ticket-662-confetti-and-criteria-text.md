---
id: ticket-662
title: "Confetti cover the whole room, and judged criteria keep their text"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-662 — Des confettis sur toute la pièce, et le texte des critères jugés

## Objectif
Que la fête d'un merge couvre toute la pièce, et que le tableau blanc affiche le
texte de chaque critère jugé.

## Contexte
Retours du 28/10 :
- les confettis ne tombaient que sur la gauche de la pièce : leurs abscisses
  étaient en pixels d'un repère de 800 px, alors qu'une pièce en fait 1100 à 1500 ;
- une fois les critères validés, le tableau listait « critère 1, critère 2, … ».
  Depuis la sortie structurée du validateur (ticket-613), un critère n'exige que
  son `index` : `_reconcile_criteria` (`services/validator.py`) recopiait alors le
  `criterion` vide de la réponse au lieu du texte envoyé. Le `validation_done` du
  run ed6f5f9f le montre : cinq critères, tous avec `"criterion": ""`.

## Solution proposée
- `lib/bureau/confettis.ts` donne l'abscisse en pourcentage de la pièce.
- `_reconcile_criteria` garde le texte du critère envoyé, et ne prend de la
  réponse que `passed` et `note`.

## Critères d'acceptation
- [x] Un test vérifie que les confettis vont de moins de 15 % à plus de 85 % de la largeur
- [x] Un test du validateur vérifie qu'un critère jugé par son seul `index` garde le texte envoyé, avec la note de la réponse

## Ce que ça ne fait pas
- Ne réécrit pas les `validation_done` déjà émis : leurs tableaux gardent « critère N ».
