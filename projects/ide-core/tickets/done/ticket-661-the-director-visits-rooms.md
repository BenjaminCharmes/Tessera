---
agent: codeur
created: 2026-10-28
depends_on:
- ticket-631
estimated_days: 2
id: ticket-661
plan: true
pr_number: 752
priority: low
status: done
title: The director walks to a room whose run turns silent or frozen, or that the
  user opens, then goes back
type: feat
---

# ticket-661 — Le directeur fait sa ronde

## Objectif
Que le directeur, c'est-à-dire l'utilisateur, passe voir les agents quand il y a
une raison de le faire.

## Contexte
Idée de Benjamin du 28/10 : le directeur passe derrière les agents des projets en
cours, de temps en temps. ADR-058 interdit une ronde au hasard : chaque mouvement
doit dire un fait. Deux faits existent déjà :
- la santé d'un run, `silencieux` ou `figé ?` (`lib/santeAgent.ts`, la pastille de la pièce) ;
- le choix de l'utilisateur : un agent cliqué (`PanneauAgentChoisi`) ou le bouton « Fil » d'une pièce.

## Solution proposée
- Quand un run passe `silencieux` ou `figé ?`, ou quand l'utilisateur choisit un
  agent ou ouvre le fil d'une pièce, le directeur quitte son bureau, se tient
  derrière l'agent concerné pendant `DUREE_DE_VISITE_MS`, puis revient.
- Une seule visite à la fois. Un délai minimal `ECART_ENTRE_VISITES_MS` sépare deux
  visites dues à la santé ; un choix de l'utilisateur passe avant.
- Une question en attente le retient à son bureau (ADR-025) : il ne part pas, et
  une visite en cours s'arrête.
- La logique est une fonction pure de l'état des runs, du choix et de l'horloge de
  la vue, sans minuteur de plus.

## Critères d'acceptation
- [ ] Un test vérifie que le directeur se rend dans la pièce d'un run qui passe `silencieux`, derrière l'agent occupé, puis revient à son bureau après `DUREE_DE_VISITE_MS`
- [ ] Un test vérifie qu'un agent choisi par l'utilisateur fait venir le directeur dans sa pièce, même pendant `ECART_ENTRE_VISITES_MS`
- [ ] Un test vérifie que deux runs silencieux à la suite ne donnent qu'une visite tant que `ECART_ENTRE_VISITES_MS` n'est pas écoulé
- [ ] Un test vérifie qu'une question en attente garde le directeur à son bureau
- [ ] Un test vérifie que la vue ne monte toujours qu'un seul intervalle

## Ce que ça ne fait pas
- Pas de ronde au hasard : sans fait à montrer, le directeur reste à son bureau (ADR-058).