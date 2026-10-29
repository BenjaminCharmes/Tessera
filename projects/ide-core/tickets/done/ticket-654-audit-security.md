---
agent: architect
created: 2026-10-28
depends_on: []
estimated_days: 1
id: ticket-654
plan: true
pr_number: null
priority: high
status: done
title: 'Audit: security review of the backend, the agent guards and the frontend'
type: design
---

# ticket-654 — Audit de sécurité

## Objectif
Faire une revue de sécurité de l'ensemble, au-delà du diff qu'audite chaque run.

## Contexte
L'agent `securite` audite le diff de chaque run, pas le code déjà en place.
Les surfaces sensibles :
- l'API, ouverte quand `STATIC_TOKEN` est vide (défaut) ;
- les gardes des agents : écriture hors projet, git en écriture, `Bash`.
  ADR-031 dit que le contrôle d'écriture sur `Bash` attrape une erreur, pas
  une évasion ;
- les chemins reçus par `routers/fs.py` ;
- les jetons de services en ligne gardés dans le `.env` (ADR-053) ;
- les termes interdits (ADR-050).

## Solution proposée
- Revue des routes : entrées non validées, chemins, injection de commande.
- Revue des gardes `PreToolUse` : contournements connus, tournures non couvertes.
- Revue du frontend : `dangerouslySetInnerHTML`, liens ouverts sans `noopener`,
  jetons exposés.
- Classer chaque constat en `CRITICAL`, `HIGH`, `MEDIUM` ou `LOW`, comme l'audit des runs.

## Critères d'acceptation
- [ ] `docs/audit/securite.md` liste chaque constat avec sa gravité, son `fichier:ligne` et un scénario d'exploitation
- [ ] `docs/audit/securite.md` dit, pour chaque garde d'ADR-027 et d'ADR-031, si un test couvre ses contournements connus
- [ ] Le livrable liste les tickets de correction, `CRITICAL` et `HIGH` d'abord, chacun avec ses critères vérifiables

## Ce que ça ne fait pas
- Ne corrige rien : ticket d'audit.
- N'écrit aucun exploit opérationnel : un scénario décrit, il ne s'exécute pas.