---
id: ticket-197
title: "Le coût d'un run se lit pendant qu'il tourne"
type: feat
status: in-progress
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-26
---

# ticket-197 — Le coût d'un run se lit pendant qu'il tourne

## Objectif

Voir, pendant un run, ce qu'il a déjà coûté, combien de tours d'outils
l'agent en cours a consommés, et où en est le plafond du run.

## Contexte

Le coût n'apparaît qu'après coup, dans `CostView` et `UsageDashboard`. Dans
`SupervisionView`, un run créé côté client part de `cout_usd: 0` et rien ne
le met à jour (`supervisionEvents.ts:59`), alors que `run_registry.py:47`
tient `cout_usd` et que chaque `agent_done` porte le coût de l'appel.
`RunView` et `AgentPanel` ne montrent rien. Or c'est pendant le run qu'on
décide de l'arrêter : un codeur à 60 lectures et 1,50 $ au tour 1 est un
signal qu'on veut voir avant le tour 3.

## Solution proposée

- Backend : l'événement `agent_tool_use` existe ; `RunActif` gagne un
  compteur d'appels d'outils de l'agent en cours, remis à zéro à chaque
  `agent_started`, et l'instantané du run le porte avec `cout_usd`.
- Frontend : `supervisionEvents.ts` applique `agent_done` au `cout_usd` du
  run et `agent_tool_use` au compteur ; `RunCard`, `RunView` et
  `AgentPanel` affichent « 0,84 $ · 3 appels · 47 outils » sur une ligne,
  avec le plafond du run à côté quand il est non nul (« sur 5,00 $ »).
- Le plafond du run et le plafond par appel viennent d'un nouvel endpoint
  `GET /config/limits`, lu une fois au chargement.
- Couleurs selon ADR-026 : `amber` au-delà de 70 % du plafond, `red` au
  delà de 90 %. Jamais de violet.

## Critères d'acceptation

- [ ] Un test backend vérifie que le compteur d'outils est remis à zéro sur
      `agent_started` et présent dans l'instantané
- [ ] Un test frontend vérifie qu'un `agent_done` de 0,40 $ puis un de
      0,20 $ donnent 0,60 $ sur la carte du run
- [ ] Un test frontend vérifie que le compteur d'outils repart à zéro quand
      un nouvel agent démarre
- [ ] Un test vérifie la couleur `amber` à 70 % et `red` à 90 %
- [ ] Un F5 pendant le run retrouve le coût cumulé depuis l'instantané
- [ ] Le test de la palette (ADR-026) passe
- [ ] `uv run pytest`, `npm run test`, `npm run build` passent

## Ce que ça ne fait pas

Pas d'historique des coûts par jour ni de budget mensuel : autre ticket.
Pas d'arrêt automatique : c'est ticket-191 pour le plafond, et le bouton
existant pour la main.

## Dépendances

Aucune ; se combine avec ticket-191.

## Estimation

1 jour.

## Risques

Le coût d'un appel n'est connu qu'à la fin de l'appel : entre deux
`agent_done`, l'affichage est en retard d'un appel. Le compteur d'outils est
ce qui bouge en temps réel, et c'est lui qui dit qu'un agent tourne en rond.
