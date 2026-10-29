---
agent: architect
created: 2026-10-28
depends_on: []
estimated_days: 1
id: ticket-626
plan: true
pr_number: 737
priority: low
status: done
title: 'Design: a server-room view of running apps, with each product''s own agents'
type: design
---

# ticket-626 — Conception : la salle des serveurs des apps lancées

## Objectif
Décider si la vue « En cours » devient une salle des serveurs, une salle par app
lancée, avec les agents propres à chaque produit, et d'où viendrait leur activité.

## Contexte
Idée de Benjamin le 28/10 : dans « En cours », une vue façon Bureau, avec une
salle par projet lancé et des bureaux pour les agents de ce produit. Par exemple,
l'agent qui fait passer les entretiens dans le cockpit Carrière, celui qui fait
les revues de produit d'Affût, ou la revue de Vigie.

La contrainte : rien n'est décoratif (ADR-058). D'une app lancée, Tessera ne
connaît aujourd'hui que son processus, ses ports et sa sortie (`AppEnCours` et
`ServiceActif` dans `frontend/src/types/api.ts`). L'activité des agents d'un
produit vit dans ce produit, et rien ne la remonte à Tessera.

## Solution proposée
- Recenser, pour chaque projet qui déclare des `services` dans son `agents.json`,
  les agents IA qu'il fait tourner et ce qu'il expose déjà (route, fichier, journal).
- Comparer les sources possibles de leur activité : une route de santé enrichie
  que Tessera interroge, des lignes structurées dans la sortie du service, ou un
  fichier d'état. Critères de choix : effort par produit, coût en tokens nul,
  échec fermé (une app muette ne dessine personne).
- Recommander d'adopter, de réduire (une salle sans agents, avec seulement
  l'état de l'app) ou d'écarter.

## Critères d'acceptation
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit la source retenue pour l'activité des agents d'un produit, ou pourquoi l'idée est réduite ou écartée
- [ ] Le livrable liste, pour chaque projet qui déclare des `services`, les agents IA qu'il fait tourner et ce qu'il expose déjà, avec le fichier qui le prouve
- [ ] Le livrable liste les tickets d'implémentation qui en découlent, chacun avec ses critères vérifiables, en commençant par la maquette de la vue

## Ce que ça ne fait pas
- N'implémente rien : ticket de conception.
- Ne dessine pas la maquette : elle se fait avant toute interface, sur le compte de Benjamin.