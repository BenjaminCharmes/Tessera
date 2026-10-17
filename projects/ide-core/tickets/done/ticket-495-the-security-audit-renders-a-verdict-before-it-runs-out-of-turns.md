---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.5
id: ticket-495
pr_number: null
priority: high
status: done
title: The security audit renders a verdict before it runs out of tool turns, and
  falls back to the diff alone when it does
type: fix
---

# ticket-495 — L'audit de sécurité rend un verdict avant d'épuiser ses tours

## Objectif

Un gros diff ne fait plus échouer l'audit sur sa limite de tours : l'audit
conclut avec ce qu'il a lu, ou retombe sur l'audit du diff seul.

## Contexte

16/10 soir, Kadoomi ticket-014, premier gros diff depuis le ticket-485
(32 fichiers, 702 lignes) : l'audit, qui lit désormais le projet avec
`Read`, `Glob` et `Grep`, a dépassé les 20 tours (`llm_max_turns_reviewer`,
partagé avec le rôle `securite` par `_tours_du_role`) sans rendre de verdict.
`SecurityAuditorService` a reçu « Reached maximum number of turns (20) »,
l'a traité comme un provider indisponible et a rendu `BLOCK` avec zéro
faille (ADR-039). La file s'est interrompue alors que le testeur était vert.
Avant le 485, le même diff aurait été jugé en un appel, sans outil.

## Solution proposée

1. **Un budget propre au rôle** : `llm_max_turns_securite` dans `Settings`
   (défaut 30), utilisé par `_tours_du_role("securite")`.
2. **Le prompt annonce le budget** : « Tu disposes d'au plus N lectures.
   Lis d'abord ce qui peut changer un BLOCK en PASS ; garde le dernier tour
   pour ton verdict. Un point que tu n'as pas pu vérifier se signale dans
   `summary`, il ne bloque pas. » Le nombre vient du réglage, pas du texte.
3. **Repli sur le diff seul** : si l'appel avec outils échoue sur la limite
   de tours, `SecurityAuditorService` refait **un** appel sans outil, sur le
   diff seul, comme avant le 485, et émet `security_audit_fallback`. Si ce
   second appel échoue, la porte reste fermée : `BLOCK` (ADR-039).

## Ce que ça ne fait pas

- Ne change pas la règle « audit indisponible = BLOCK » : le repli est un
  second essai, pas une ouverture.
- Ne relève pas le budget du reviewer.

## Critères d'acceptation

- [ ] Un test vérifie que le rôle `securite` reçoit `llm_max_turns_securite`
      et le reviewer son propre réglage
- [ ] Un test vérifie que le prompt contient le budget tiré du réglage
- [ ] Un test vérifie qu'une erreur de limite de tours déclenche un second
      appel sans outil, dont le verdict est retenu, avec l'événement
- [ ] Un test vérifie que deux échecs successifs rendent `BLOCK`
- [ ] Un test vérifie qu'une autre erreur du premier appel ne déclenche pas
      de repli et rend `BLOCK`