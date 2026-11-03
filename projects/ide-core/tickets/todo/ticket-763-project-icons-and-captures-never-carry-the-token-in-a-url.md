---
id: ticket-763
title: "Project icons and run captures never carry the token in a URL"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-763 — Les icônes de projet et les captures ne portent jamais le jeton dans une URL

## Objectif

Avec `STATIC_TOKEN` renseignée, les icônes et les captures s'affichent, et le jeton
n'apparaît dans aucune URL HTTP.

## Contexte

Audit du 30/10 (relecture du 03/11), tickets 721 et 726.
`frontend/src/components/ProjetsView/IconeDuProjet.tsx` ajoute `?token=` à une requête HTTP
(`withTokenQuery`) ; `backend/src/tessera/auth.py` n'accepte `?token=` que sur une WebSocket,
justement parce qu'une URL finit dans les journaux d'accès. Résultat : 401 sur chaque icône
(repli sur l'initiale) et jeton en clair dans les journaux. `urlDeCapture`
(`frontend/src/components/RunView/capturesDuRun.ts` ou voisin) pose un `<img>` sans jeton.

## Solution proposée

Charger l'image par le client HTTP commun (en-tête `Authorization`), puis
`URL.createObjectURL`, libéré au démontage.

## Critères d'acceptation

- [ ] Un test vérifie, avec `VITE_STATIC_TOKEN` stubbé, qu'aucun `src` rendu par
      `IconeDuProjet` ne contient `token=` et que la requête de l'icône porte l'en-tête
      `Authorization`
- [ ] Le même test pour l'image d'une capture de run
- [ ] Un test vérifie que l'URL objet est révoquée au démontage
