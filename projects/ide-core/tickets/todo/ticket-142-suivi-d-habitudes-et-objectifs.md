---
id: ticket-142
title: "Projet : suivi d'habitudes et d'objectifs personnels"
type: design
status: todo
pr_number: null
priority: low
agent: architect
depends_on: ["ticket-136"]
estimated_days: 1
created: 2026-09-23
---

# ticket-142 — Suivi d'habitudes et d'objectifs

## Objectif

Cadrer un projet construit par Tessera : suivre des habitudes quotidiennes et
des objectifs — ce qui est fait, les séries, ce qui décroche.

## Contexte

Retenu parmi les candidats au projet from-scratch (ticket-136). Ce qu'il
apporte de spécifique à l'exercice : c'est le seul des candidats dont la stack
est **exactement** celle de Tessera — React, FastAPI, SQLite. Le pipeline y
travaille en terrain connu, ce qui isole la question « l'orchestration
tient-elle ? » de la question « le modèle connaît-il cette techno ? ».

C'est aussi le plus classique des quatre : un CRUD avec des séries et des
statistiques. Ce n'est pas un défaut ici — un projet banal donne une mesure
propre, parce que rien d'inhabituel ne vient expliquer un échec.

## La frontière à tracer

Le cockpit Carrière (ticket-133) porte le **professionnel** : compétences,
entretiens, rémunération. Ce projet porte le **personnel** : sport, lecture,
régularité.

Le mot « objectifs » appartient aux deux, et c'est là que les deux projets
peuvent se mettre à se recouvrir. À trancher au cadrage, faute de quoi la
même chose se saisira à deux endroits — exactement ce qui a fait écarter le
générateur de CV comme projet séparé.

## Solution proposée

À trancher au moment du cadrage :

1. Ce qu'on suit : des habitudes binaires (fait / pas fait), des quantités,
   ou les deux ?
2. La granularité — quotidienne, hebdomadaire, libre ?
3. Ce qu'on montre : une série en cours, un historique, des statistiques ?
   Chacun coûte un écran.
4. Où passe la frontière avec Carrière (voir ci-dessus).
5. Les données restent-elles locales, comme Carrière, ou n'ont-elles rien de
   sensible ?

## Critères d'acceptation

- [ ] Les cinq questions ci-dessus ont une réponse écrite
- [ ] La frontière avec le cockpit Carrière est explicite : ce qui va où, et
      ce qui ne se saisit qu'à un seul endroit
- [ ] La liste des écrans est arrêtée, avec une phrase par écran
- [ ] Le backlog initial est créé dans le projet, pas dans `ide-core`
- [ ] Le niveau d'`autonomy` du projet est arrêté (ADR-029)

## Dépendances

ticket-136.

## Estimation

1 jour de cadrage.

## Risques

Le recouvrement avec Carrière est le vrai risque : deux applications qui
suivent « mes objectifs » finiraient par se contredire, et c'est celle qu'on
consulte le moins qui dériverait.

---

## Décision d'ordonnancement — 2026-09-23

Ce projet **attend** que l'exercice du démineur (ticket-136) ait produit sa
mesure. Le cadrer maintenant produirait des décisions que cet exercice peut
invalider, et deux projets d'essai lancés ensemble ne se comparent plus.

Sa place dans la file est fixée : **deuxième** — il ajoute le backend et la base, sur exactement la stack de Tessera. Après un démineur purement frontend, c'est la dimension suivante, et la seule.

Le cadrage reste à faire, et c'est à ce moment-là que les questions ouvertes
de ce ticket se tranchent.
