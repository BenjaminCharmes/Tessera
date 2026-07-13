---
id: ticket-042
title: "Coverage frontend — monter à 80 % sur les composants clés"
type: chore
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1.5
created: 2026-07-13
---

# ticket-042 — Coverage frontend : de 66 % à 80 %

## Objectif

Monter la couverture de tests frontend de **66 % (statements)** à **80 %**,
en ciblant les composants et modules actuellement peu ou pas testés.

## Contexte

Couverture actuelle (2026-07-13) :
- Statements : 65.93 % (544/825)
- Branches   : 53.47 % (331/619)
- Functions  : 55.55 % (155/279)
- Lines      : 66.97 % (501/748)

Les zones non couvertes les plus impactantes :
- `lib/api.ts` : 41.93 % — client HTTP partagé par toute l'UI
- `lib/fs.ts` : 0 % — accès filesystem Tauri
- `lib/ws.ts` : 16.66 % — client WebSocket
- Composants AgentPanel (PipelineSummary), modales CreateProject/CreateTicket/ImportProject
- `RunHistory` (branches non couvertes)

## Solution proposée

Écrire des tests Vitest + React Testing Library pour :

1. **`lib/api.ts`** — mocker `fetch`, couvrir les cas d'erreur HTTP (4xx, 5xx, réseau)
2. **`lib/ws.ts`** — mocker WebSocket, tester connect/disconnect/message/erreur
3. **`components/AgentPanel/PipelineSummary`** — render avec différents états de pipeline
4. **Modales** — CreateProjectModal, CreateTicketModal, ImportProjectModal :
   formulaire valide, formulaire invalide, soumission, fermeture
5. **`RunHistory`** — branches manquantes (run en cours, run sans coût, run approuvé/rejeté)

`lib/fs.ts` (Tauri filesystem) : mocker `@tauri-apps/api` pour éviter les dépendances
natives dans les tests.

## Critères d'acceptation

- [ ] Statements coverage ≥ 80 %
- [ ] Branches coverage ≥ 70 %
- [ ] `npm run test:coverage` passe avec les seuils mis à jour dans `vitest.config.ts`
- [ ] Aucun test existant ne régresse

## Dépendances

Aucune.

## Estimation

**1.5j** — Écriture de tests uniquement, pas de code applicatif.
