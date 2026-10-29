---
agent: architect
created: 2026-10-28
depends_on: []
estimated_days: 1
id: ticket-652
plan: true
pr_number: 762
priority: medium
status: done
title: 'Audit: find duplicated logic and components, and what should be shared'
type: design
---

# ticket-652 — Audit des doublons et de la réutilisation

## Objectif
Repérer ce qui est écrit deux fois, dans le backend comme dans le frontend, et
ce qui devrait passer par un composant ou un module partagé.

## Contexte
Le reviewer et le validateur ne lisent qu'un diff : une duplication entre deux
fichiers qu'un ticket ne touche pas leur échappe. Le 28/10, on en a trouvé
plusieurs :
- `Salle.tsx` et `FondDeLaPiece.tsx` dessinaient chacun leur mur ;
- l'interrupteur ne suivait pas l'échelle commune des sprites ;
- `getPrStatuses` lisait mal sa route depuis le ticket-367, et tous les tests
  le masquaient avec un mock au mauvais format.

Le Bureau a son ticket de consolidation (ticket-631). Cet audit couvre le reste.

## Solution proposée
- Backend : services qui refont la même lecture (`agents.json`, git, tickets),
  helpers dupliqués, routes au contrat proche.
- Frontend : hooks de lecture, composants d'UI voisins (boutons, bulles,
  pastilles), lectures d'API dont le mock de test n'a pas la forme de la vraie
  réponse.

## Critères d'acceptation
- [ ] `docs/audit/doublons.md` liste chaque doublon trouvé avec les `fichier:ligne` de ses copies
- [ ] `docs/audit/doublons.md` liste les appels d'API du frontend dont le type déclaré diffère du modèle de réponse de la route backend
- [ ] Le livrable liste les tickets de mise en commun, chacun avec ses critères vérifiables, sans recouvrir le ticket-631

## Ce que ça ne fait pas
- Ne refactore rien : ticket d'audit.