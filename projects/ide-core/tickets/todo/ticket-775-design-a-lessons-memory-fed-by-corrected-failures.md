---
id: ticket-775
title: "Design a per-project lessons memory fed by corrected failures"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-775 — Concevoir une mémoire de leçons par projet, nourrie par les échecs corrigés

## Objectif

Un agent de Tessera ne refait pas une erreur qu'un run précédent du même projet a déjà
faite et corrigée.

## Contexte

Le 03/11, ticket-736 a perdu trois tours : à chaque tour, un autre double de test ne
connaissait pas la nouvelle méthode du workspace. Rien n'a transmis la leçon d'un tour à
l'autre, ni d'un ticket au suivant. Un IDE comparable tient un fichier de leçons court par
projet : après un échec corrigé, l'agent suivant reçoit l'erreur et ajoute une leçon
(« Quand <situation>, <action>. (source : ticket, date) ») ; le fichier est transmis à chaque
agent ; une leçon qui affaiblit les tests ou la CI est refusée ; au-delà de 40 leçons ou de
6 Ko, un compactage est demandé.

## Ce que la conception doit fixer

- Où vit le fichier (artefact Tessera, ADR-021 et ADR-023), qui l'écrit (un agent, ou le
  service sur proposition, comme la description d'ADR-068), et comment il est relu.
- Sa place dans le contexte des agents, face à `contraintes.md` et au plafond de taille.
- Le contrôle d'une leçon : affaiblir une vérification, doublon, longueur.
- Son articulation avec `memory/decisions.md` : une leçon n'est pas une décision.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md` répond à
      chacun des points ci-dessus et cite le ticket-736 comme cas d'origine
- [ ] Les tickets d'implémentation sont créés dans `projects/ide-core/tickets/todo/`, chacun
      tient en moins d'une journée et nomme ses tests
- [ ] Aucun code n'est écrit par ce ticket
