---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 0.5
id: ticket-886
pr_number: null
priority: low
status: done
title: The supervision badge test renders the count with a pipeline run and a chat
type: test
---

# ticket-886 — The supervision badge test renders the count with a pipeline run and a chat

## Objectif

Le test « compte le chat parmi ce qui tourne » rend vraiment le compteur au lieu de relire sa fixture.

## Contexte

Trouvé par l'essai de seconde revue (ticket-846, `docs/essais/seconde-revue.md`) : le reviewer l'a relevé sur un commit classé sain, un humain l'a confirmé, et le défaut est toujours sur `develop` le 06/11. Entrée s11, ticket-130.

Dans `frontend/src/components/SupervisionView/SupervisionView.test.tsx`, ce test construit une supervision avec un run de pipeline et un chat, puis vérifie que `sup.runs` a deux éléments : il ne rend aucun composant et passerait même si les chats étaient exclus de l'affichage.

## Solution proposée

Rendre le composant qui affiche le nombre de runs en cours, avec un run de pipeline et un chat, et lire le nombre affiché.

## Critères d'acceptation

- [ ] Le test rend un composant avec un run de pipeline et un run `mode: "chat"` et vérifie que le nombre affiché est 2.
- [ ] Le test ne lit plus `sup.runs` directement.

## Dépendances

Aucune.

## Estimation

Une demi-journée au plus.

## Ce que ça ne fait pas

Ne revoit pas le reste du ticket d'origine : seulement le défaut confirmé.