---
id: ticket-778
title: "Any agent can be chosen in the Bureau, done or waiting, not only a working one"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-778 — Tout agent se choisit dans le Bureau, qu'il ait fini ou qu'il attende

## Objectif

Le panneau « Agent choisi » répond pour chaque agent, pas seulement pour celui qui travaille.

## Contexte

Demandé par Benjamin le 04/11 : seul un agent au travail se choisissait. `PosteDeTravail`
ne branchait le clic que sur un poste `occupe`, et `lignesDeLAgent` rendait `null` pour un
poste `fait` ou `libre`. Un agent qui a fini quitte son poste pour se promener (café,
machine) : il ne se cliquait nulle part.

## Solution

Faite à la main.
- Tout poste se choisit ; un agent qui se promène se choisit là où il est, au clic et au
  clavier (`AgentsDeLaPiece`).
- `lignesDeLAgent` (`frontend/src/lib/bureau/agentChoisi.ts`) : au travail, comme avant ;
  fini, « A rendu » (son code, tests verts ou rouges, audit, approuvé ou changements
  demandés, critères validés ou refusés) et « Fini, il y a… », lus dans son dernier
  événement de fin ; en attente, « Il attend : la fin de <poste au travail> ».
- L'invite devient « Clique un agent ».

## Critères d'acceptation

- [x] `agentChoisi.test.ts` couvre un agent qui a fini (rendu, depuis quand), le verdict du
      reviewer et un agent en attente
- [x] `Piece.test.tsx` vérifie que chaque poste se choisit, fini et en attente compris
- [x] `PanneauAgentChoisi.test.tsx` vérifie le panneau d'un agent en attente
- [x] `AgentsDeLaPiece.test.tsx` vérifie qu'un agent qui se promène se choisit au clic et au
      clavier, et reste une image quand personne n'écoute le choix

## Ce que ça ne fait pas

« À toi » ne change pas (choix de Benjamin). Pas de « Lui écrire » : le canal d'écriture
n'est toujours pas câblé dans le Bureau.
