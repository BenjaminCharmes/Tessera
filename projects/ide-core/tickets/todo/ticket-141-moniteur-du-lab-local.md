---
id: ticket-141
title: "Projet : moniteur du lab local (NAS, GPU, modèles)"
type: design
status: todo
pr_number: null
priority: low
agent: architect
depends_on: ["ticket-136"]
estimated_days: 1
created: 2026-09-23
---

# ticket-141 — Moniteur du lab local

## Objectif

Cadrer un projet construit par Tessera : suivre l'état d'un lab à la maison —
NAS, charge GPU/CPU, mémoire, modèles chargés localement.

## Contexte

Retenu parmi les candidats au projet from-scratch (ticket-136). Ce qu'il
apporte de spécifique : il prépare une infrastructure qui n'existe pas encore,
et il donne de la matière aux articles du portfolio (ticket-135) — héberger
des modèles en local, automatiser des processus chez soi.

C'est aussi celui dont les critères de ticket-136 tiennent le moins bien : le
matériel n'est pas là. Les tests porteraient sur des **sondes simulées**,
donc sur l'interface entre le moniteur et sa source, pas sur des mesures
réelles. Ce n'est pas rédhibitoire — c'est même une bonne architecture — mais
il faut le décider exprès.

## Solution proposée

À trancher au moment du cadrage :

1. L'ordre : ce projet attend-il que le matériel soit là, ou le précède-t-il
   en travaillant sur des sondes simulées ?
2. La source des mesures — `psutil` en local, une API sur le NAS, `nvidia-smi`
   pour le GPU ? Chacune a une disponibilité différente.
3. Où il tourne : sur la machine mesurée, ou sur une autre qui l'interroge ?
   Le second cas ouvre une surface réseau qu'il faut décider.
4. Ce qu'on garde : un affichage temps réel seulement, ou un historique ?
5. Ce que « modèles chargés » veut dire concrètement — Ollama, llama.cpp,
   autre chose ? La réponse conditionne toute une partie du projet.

## Critères d'acceptation

- [ ] Les cinq questions ci-dessus ont une réponse écrite
- [ ] La décision dit explicitement si on démarre avant le matériel, et sur
      quelles sondes simulées
- [ ] L'interface entre le moniteur et ses sources est définie, de façon à ce
      qu'une sonde réelle remplace une simulée sans changer le reste
- [ ] Si le moniteur écoute sur le réseau, ce qui l'expose est décidé et écrit
- [ ] Le backlog initial est créé dans le projet, pas dans `ide-core`

## Dépendances

ticket-136.

## Estimation

1 jour de cadrage.

## Risques

Un projet qui mesure du matériel absent risque de mesurer surtout son propre
simulateur. L'exigence sur l'interface est ce qui le rend utile quand même :
le jour où le NAS arrive, seule la sonde change.
