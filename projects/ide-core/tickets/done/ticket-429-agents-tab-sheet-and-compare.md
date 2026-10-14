---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 1
id: ticket-429
pr_number: null
priority: medium
status: done
title: The Agents tab shows a role sheet with its 30-day figures and last verdicts,
  and a view comparing every role
type: feat
---

# ticket-429 — Onglet Agents : fiche d'un rôle et comparaison

## Objectif

Comprendre d'un coup d'œil ce que fait un rôle du pipeline, ce qu'il coûte
et ce qu'il décide, et comparer les rôles entre eux.

## Contexte

L'onglet Agents a déjà sa vue centrale (`components/AgentDetail/`, prompt
et modèle d'un rôle). Maquette validée :
`projects/ide-core/design/maquette/Agents.dc.html`. Données disponibles :
`GET /api/v1/agents/{role}` (prompt, intégré ou non),
`GET /api/v1/usage/stats?days=30&project_id=…` (`per_agent` : une ligne par
rôle avec appels, tokens et coût), `GET /api/v1/projects/{id}/runs`.

## Solution proposée

- En-tête : titre « Agents » et un sélecteur « Fiche » (défaut) /
  « Comparer ».
- **Fiche** (maquette) : à gauche, le rôle, une phrase sur ce qu'il fait
  (description du registre, sinon la première ligne de son prompt), le
  prompt système (existant), ses derniers verdicts quand le rôle rend un
  verdict (reviewer, validateur, sécurité) ; à droite, la configuration
  (modèle et repli, existants) et les chiffres sur 30 jours pour le projet
  actif : appels, coût, depuis `per_agent`.
- **Comparer** : un tableau, une ligne par rôle actif du projet : rôle,
  modèle, appels et coût sur 30 jours ; un clic sur une ligne ouvre sa
  fiche.
- Un rôle sans appel sur la période affiche « — », pas 0 $.

## Critères d'acceptation

- [ ] Un test vérifie que la fiche affiche les appels et le coût du rôle
      tirés de `per_agent`, et « — » pour un rôle absent de `per_agent`
- [ ] Un test vérifie que le sélecteur bascule vers « Comparer » et affiche
      une ligne par rôle actif avec son modèle
- [ ] Un test vérifie qu'un clic sur une ligne du tableau ouvre la fiche de
      ce rôle
- [ ] Les tests existants d'`AgentDetail` et de `ModelPicker` restent verts

## Dépendances

Aucune.

## Ce que ça ne fait pas

- Pas de durée médiane ni de taux d'approbation par rôle : la maquette les
  montrait, mais aucun endpoint ne les fournit encore.