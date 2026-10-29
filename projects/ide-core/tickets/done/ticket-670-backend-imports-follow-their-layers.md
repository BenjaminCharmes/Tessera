---
agent: codeur
created: 2026-10-29
depends_on: []
estimated_days: 1
id: ticket-670
pr_number: null
priority: low
status: done
title: A test keeps backend imports flowing from routers to services to models
type: chore
---

# ticket-670 — Les imports du backend suivent leurs couches

## Objectif
Qu'un import à contresens entre couches du backend se voie en CI, comme un fichier
trop long se voit déjà.

## Contexte
Piste reçue le 29/10 d'une session tierce (contrôles qualité en CI). Deux de ses
trois points existent déjà : les plafonds de longueur
(`backend/tests/test_longueur_des_fichiers.py`, `frontend/src/longueur-des-fichiers.test.ts`)
et la couverture (tickets 038 et 042). Le sens des imports n'est mesuré nulle part.

## Solution proposée
Un test lit, par `ast`, les imports de chaque module de `backend/src/tessera/` et
vérifie le sens des couches : `routers` peut importer `services` et `models` ;
`services` peut importer `models` ; `models` n'importe ni `services` ni `routers`.
Les écarts existants sont listés dans le test, comme les plafonds : la liste ne
peut que raccourcir.

## Critères d'acceptation
- [ ] `backend/tests/test_sens_des_imports.py` échoue quand un module de `models/` importe `services` ou `routers`, ou qu'un module de `services/` importe `routers`
- [ ] Les écarts présents au moment du ticket sont listés nommément dans le test, et un écart corrigé mais toujours listé fait échouer le test

## Ce que ça ne fait pas
- Ne corrige pas les écarts existants : l'audit des refactos (ticket-653) les classera.