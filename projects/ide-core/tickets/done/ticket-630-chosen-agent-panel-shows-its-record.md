---
agent: codeur
created: 2026-10-28
depends_on:
- ticket-628
estimated_days: 1
id: ticket-630
pr_number: null
priority: low
status: done
title: The chosen-agent panel shows the agent's record on its project
type: feat
---

# ticket-630 — Le bilan de l'agent choisi

## Objectif
Donner du sens au nom d'un agent : ce qu'il a fait sur son projet.

## Contexte
Le panneau « Agent choisi » (`PanneauAgentChoisi.tsx`, `lib/bureau/agentChoisi.ts`)
ne montre que le run en cours. Les données d'un bilan existent déjà :
- `firstTryCount` (`lib/bureau/weekEmployee.ts`) compte les runs approuvés au
  premier tour sur la semaine, et sert à élire l'employé de la semaine ;
- `GET /api/v1/projects/{project_id}/usage/breakdown` donne le coût cumulé par rôle.

## Solution proposée
Sous les lignes du run, une section « Bilan » :
- runs de la semaine sur ce projet, dont ceux approuvés au premier tour (`firstTryCount`) ;
- coût cumulé du rôle sur ce projet, lu dans `usage/breakdown`.

Sans donnée, la ligne ne s'affiche pas : on n'écrit pas « 0 » faute de savoir.

## Critères d'acceptation
- [ ] Un test vérifie que le panneau affiche, pour l'agent choisi, le nombre de runs de la semaine et celui des runs approuvés au premier tour, calculé par `firstTryCount`
- [ ] Un test vérifie que le panneau affiche le coût cumulé du rôle sur le projet, lu dans `usage/breakdown`
- [ ] Un test vérifie qu'une lecture de `usage/breakdown` en échec retire la ligne du coût sans retirer le reste du panneau

## Ce que ça ne fait pas
- N'ajoute aucune route backend.