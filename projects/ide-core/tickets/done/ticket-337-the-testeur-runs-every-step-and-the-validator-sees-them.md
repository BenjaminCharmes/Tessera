---
id: ticket-337
title: "The testeur runs every step of an && chain, and the validator sees each step with its exit code"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-337 — Le testeur lance chaque étape, et le validateur les voit

## Objectif

Que « typecheck, lint, test et build passent » soit vrai quand le testeur le
dit, et vérifiable par le validateur.

## Contexte

Sur le ticket-033 de démineur (2026-10-05), le validateur a refusé « typecheck,
lint, test et build passent » alors que le testeur était vert : il ne recevait
que la dernière ligne de sortie, sans la commande lancée.

En vérifiant, un défaut plus grave : le testeur lance sa commande **sans
shell**. `a && b` y devient un seul programme, `a`, qui reçoit `&&` et `b` en
arguments. Mesuré : `node -e "exit 0" && node -e "exit 4"` rendait vert.
Démineur et portfolio enchaînent leurs étapes avec `&&` et commencent par
`npm` : `npm.cmd` passe par cmd.exe, qui enchaîne — par chance, et seulement
sous Windows.

## Solution proposée

- `commande_chainee.decouper` sépare la commande sur `&&` ; les autres
  opérateurs de shell (`|`, `||`, `;`, `&`, redirections) sont refusés avec un
  message, plutôt que passés en arguments en silence.
- Le testeur lance les étapes une à une, s'arrête à la première qui échoue,
  et garde chacune avec son code de sortie (`TestResult.etapes`). Le délai
  borne la commande entière.
- Le validateur reçoit « Étapes lancées » ; son prompt juge un critère de
  commande sur ces étapes, et dit, quand il refuse un critère dont le code est
  hors du diff, que citer le fichier entre backticks le joindrait.
- Le skill `new-ticket` l'explique aux rédacteurs de tickets.

Écarté : marquer un critère invérifiable « non vérifiable » au lieu de le
refuser. Refuser par défaut est voulu (tickets 209, 219, ADR-039).

## Critères d'acceptation

- [x] Un test vérifie que `decouper` rend les étapes d'une chaîne `&&`, garde
      un `&&` entre guillemets comme argument, et refuse `|`, `||`, `;`, `>`,
      `&` et une étape vide
- [x] Un test vérifie qu'une étape tardive en échec fait échouer le testeur
      (`exit 0 && exit 4` → rouge)
- [x] Un test vérifie que la chaîne s'arrête à la première étape en échec
- [x] Un test vérifie qu'un opérateur non géré ne démarre rien
- [x] Un test vérifie que le message du validateur liste chaque étape avec son
      code de sortie

## Dépendances

Aucune.

## Estimation

0,5 jour.
