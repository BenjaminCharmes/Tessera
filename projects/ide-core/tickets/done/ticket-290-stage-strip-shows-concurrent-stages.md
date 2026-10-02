---
agent: codeur
created: 2026-10-01
depends_on:
- ticket-289
estimated_days: 1
id: ticket-290
pr_number: null
priority: high
status: done
title: The stage strip and the run feed show two stages running at once
type: feat
---

# ticket-290 — La frise montre deux étapes actives à la fois

## Objectif

Que la vue du run reste juste quand la revue et la validation tournent
ensemble : les deux pastilles actives, puis chacune terminée à son tour.

## Contexte

Le ticket-289 lance reviewer et validateur en parallèle, et ajoute
`etapes_en_cours` à l'instantané du run. Le frontend ne connaît qu'une étape :

- `StreamState.etape` est une chaîne unique (`hooks/streamState.ts`).
  `agent_started` (reviewer) la met à `revue`, `validation_started` à
  `validation` : la seconde efface la première.
- `StageStrip.tsx` (`etatEtape`) marque `active` la seule étape égale à
  `etape`, et `done` toutes celles qui la précèdent dans `ORDRE_IDS` : la
  revue s'afficherait terminée dès que la validation démarre.
- `etatDepuisRun` reconstruit l'état d'un run rejoint en cours depuis
  `run.etape` seul.

## Solution proposée

- `StreamState` porte `etapesEnCours: string[]`. Un démarrage d'étape
  l'ajoute, la fin correspondante (`agent_done` du reviewer,
  `validation_done`) l'en retire. `etape` reste la dernière démarrée.
- `etatDepuisRun` lit `etapes_en_cours`, et retombe sur `[etape]` quand le
  champ est absent.
- `StageStrip` marque `active` toute étape présente dans `etapesEnCours`.
  Une étape n'est `done` que si son événement de fin a été reçu, ou si une
  étape qui la suit **et ne tourne pas en parallèle avec elle** a démarré.
- Le fil d'entrées n'impose pas d'ordre : l'entrée du validateur peut
  arriver avant celle du reviewer d'un même tour.

## Critères d'acceptation

- [ ] Un test de `applyEvent` vérifie qu'après `agent_started` (reviewer)
      puis `validation_started`, `etapesEnCours` contient `revue` et
      `validation`
- [ ] Un test de `applyEvent` vérifie qu'un `validation_done` retire
      `validation` et laisse `revue`
- [ ] Un test de `etatDepuisRun` vérifie la lecture de `etapes_en_cours`, et
      le repli sur `etape` quand il manque
- [ ] Un test de `StageStrip` vérifie que revue et validation sont toutes
      deux actives au même moment
- [ ] Un test de `StageStrip` vérifie que la revue reste active, et non
      terminée, quand la validation finit la première

## Ce que ça ne fait pas

Aucun changement backend : l'instantané est livré par le ticket-289.

## Dépendances

ticket-289, pour `etapes_en_cours` et l'ordre réel des événements.

## Estimation

1 jour.

## Risques

`streamState.ts` est touché par les tickets 279 à 283 : relire leur version
avant de modifier le reducer.