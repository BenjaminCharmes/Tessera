---
agent: codeur
created: 2026-10-08
depends_on: []
estimated_days: 0.5
id: ticket-387
pr_number: 337
priority: high
status: done
title: The security audit blocks only on what the ticket adds; a flaw already merged
  is reported without blocking
type: fix
---

# ticket-387 — L'audit ne bloque que sur ce que le ticket ajoute

## Objectif

Qu'un ticket ne soit plus bloqué par l'audit sécurité pour du code qu'il n'a
pas écrit, sans affaiblir le blocage sur ce qu'il introduit.

## Contexte

L'audit (`backend/src/tessera/services/security_auditor.py`, prompt
`agents/prompts/securite.md`) reçoit le diff unifié du run, lignes de
contexte comprises, et bloque dès qu'il qualifie un problème `CRITICAL` ou
`HIGH` (ADR-039) — sans distinguer une ligne ajoutée (`+`) d'une ligne de
contexte.

Constaté le 2026-10-08 à 09:31:40 UTC sur vigie, signalé par la session qui
pilote ce projet : « [ticket-013] securite: BLOCK — … authentication tokens
stored in localStorage ». Ce stockage vient du ticket-012, déjà mergé ; dans
le diff du 013, `const TOKEN_KEY = …` n'est qu'en contexte, et le seul
`localStorage` ajouté est un `localStorage.clear()` dans un test. La file
s'est arrêtée ; tout ticket qui touche ce fichier serait bloqué de même.

## Solution proposée

1. Le prompt de l'audit dit que seules les lignes ajoutées par le diff (`+`)
   sont jugées ; un problème vu dans le contexte (déjà présent) est rendu avec
   `"introduced": false`.
2. Chaque entrée de `issues` porte un champ `introduced` (booléen) ; le
   parseur le lit, avec **`true` par défaut** quand il manque (échec fermé,
   ADR-039).
3. Le blocage (`BLOCK` imposé sur `CRITICAL`/`HIGH`) ne tient compte que des
   problèmes `introduced: true`. Les autres sont transmis au reviewer et
   journalisés comme « préexistant », sans bloquer.

## Critères d'acceptation

- [ ] `agents/prompts/securite.md` demande de ne juger que les lignes ajoutées et décrit le champ `introduced`
- [ ] Un test de `backend/tests/test_security_auditor.py` vérifie qu'une réponse avec un seul problème `HIGH` marqué `"introduced": false` et un verdict `PASS` rend `PASS`
- [ ] Un test de `backend/tests/test_security_auditor.py` vérifie qu'un problème `HIGH` marqué `"introduced": true` impose `BLOCK`, même si le verdict de l'auditeur est `PASS`
- [ ] Un test de `backend/tests/test_security_auditor.py` vérifie qu'un problème `HIGH` sans champ `introduced` impose `BLOCK`
- [ ] Un test de `backend/tests/test_security_auditor.py` vérifie qu'un problème préexistant figure dans le résultat transmis au reviewer

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Un auditeur qui marquerait à tort une faille nouvelle comme préexistante la
laisserait passer : le reviewer la voit toujours, et le champ manquant reste
bloquant.

## Ce que ça ne fait pas

- Ne corrige pas la faille préexistante elle-même (ticket du projet concerné).
- Ne change pas la troncature du diff à 16 000 caractères.