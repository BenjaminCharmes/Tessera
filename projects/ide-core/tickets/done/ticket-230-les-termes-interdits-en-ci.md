---
id: ticket-230
title: "Une PR qui publierait un terme interdit est refusée par la CI"
type: feat
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: ["ticket-206", "ticket-207"]
estimated_days: 0.5
created: 2026-09-29
---

# ticket-230 — Les termes interdits en CI

## Objectif

Troisième porte d'ADR-050 : ce qu'une PR publierait passe au contrôle des termes interdits sur GitHub, et le merge est impossible sans ce contrôle.

## Contexte

Le pipeline contrôle ses pushes (ticket-206), le hook ceux faits à la main (ticket-207). Restent ce qu'aucun des deux ne voit : le titre et le corps d'une PR, et un push parti d'une machine sans hook, par exemple celui d'un agent d'une autre session. Avant le passage du dépôt en public, il faut aussi pouvoir scanner tout ce qui est déjà exposé.

Fait à la main : les agents ne touchent pas à `.github/workflows/` (ADR-027).

## Solution

- `scripts/termes_interdits_ci.py`, job `termes-interdits` de `ci.yml`, déclenché aussi sur `edited`. Il réutilise les fonctions du hook (ADR-034), prend la liste dans le secret `FORBIDDEN_TERMS`, et refuse si elle est absente ou si git échoue.
- `scripts/scan_historique.py` : blobs de toutes les refs, `refs/pull/*` compris, métadonnées de commit, noms de refs, PR, issues, commentaires et releases.
- ADR-050.

## Critères d'acceptation

- [x] Un test : secret absent → PR refusée
- [x] Un test : un terme dans le corps de la PR → refus qui nomme `pr:corps`, jamais le terme
- [x] Un test : un terme dans une ligne ajoutée → refus
- [x] Un test : une erreur git → refus
- [x] Un test : le scan trouve un terme malgré la casse, les accents et les séparateurs, et ne nomme que l'emplacement
