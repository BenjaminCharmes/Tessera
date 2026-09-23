---
id: ticket-134
title: "Amorcer un projet de gestion de l'activité freelance"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-134 — Amorcer un projet de gestion de l'activité freelance

## Objectif

Décider ce qu'un projet « freelance » contient avant d'en écrire la première
ligne : suivi de l'activité, et éventuellement aide à la prospection.

## Contexte

Le besoin énoncé tient en deux morceaux qui n'ont ni le même risque ni la même
difficulté :

- **gérer** — missions, clients, temps, facturation, échéances. Des données,
  des vues, rien d'inhabituel ;
- **automatiser la prospection** — c'est là que ça se corse. Contacter des
  prospects par un moyen automatisé engage une réputation professionnelle, et
  l'envoi de messages non sollicités est encadré. Un agent qui écrit à des
  inconnus au nom de quelqu'un est une décision, pas une fonctionnalité.

À relier au projet `carriere`, qui documente déjà une clause d'exclusivité
exigeant une autorisation préalable et expresse de l'employeur pour l'activité
freelance. Les deux projets parlent du même sujet par deux bouts.

## Solution proposée

Séparer franchement les deux volets et ne cadrer que le premier dans ce
ticket :

1. **Gestion** — quelles entités (mission, client, facture, échéance), quelle
   persistance, quelles vues. Accessible depuis plusieurs postes, donc même
   question d'hébergement que ticket-133.
2. **Prospection** — **tranché : l'agent prépare, et rien de plus.** Il
   constitue des listes et documente les cibles ; la rédaction et l'envoi
   restent à la main. C'est la forme d'ADR-022 appliquée ici : le point où un
   humain tranche est ce qui rend acceptable tout le reste de
   l'automatisation.

## Critères d'acceptation

- [ ] Les entités du volet gestion sont listées, avec leurs relations
- [ ] La décision dit où vivent les données et ce qui part sur GitHub privé
- [ ] La décision rappelle que l'agent prépare seulement, et que ni la
      rédaction ni l'envoi ne lui reviennent
- [ ] Le lien avec la clause d'exclusivité documentée dans `carriere` est
      tranché : ce projet suppose-t-il l'autorisation obtenue ?
- [ ] Les tickets d'implémentation sont créés dans le projet concerné

## Dépendances

Aucune. Gagne à être fait après ticket-133, qui tranche les mêmes questions
d'hébergement et de confidentialité.

## Estimation

1 jour.

## Risques

Un agent qui envoie des messages à des tiers au nom de quelqu'un engage cette
personne. Le défaut doit être « l'agent prépare, l'humain envoie » — sur le
modèle d'ADR-022 pour le merge : le point où un humain tranche est ce qui rend
acceptable tout le reste de l'automatisation.
