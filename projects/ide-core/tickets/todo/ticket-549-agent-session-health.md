---
id: ticket-549
title: "An agent's health is visible: active, waiting, suspected stall"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-23
plan: true
---

# ticket-549 — Santé visible d'un agent en cours

## Objectif
Voir, pendant un run, si l'agent travaille, attend ou semble figé, sans
attendre les 20 minutes de `agent_silence_max_s`.

## Contexte
`providers/agent_sdk.py` coupe un agent après `agent_silence_max_s` (1200 s)
sans message, et rien n'est visible avant. Les runs figés pendant la veille
du PC ne se voyaient qu'à ce moment-là. KrumIA (revue du 23/10) dérive un état
du temps écoulé depuis le dernier événement : actif, « attente » après 30 s,
« blocage suspecté » après 180 s.

## Solution proposée
L'état se calcule côté frontend, à partir de l'horodatage du dernier
événement reçu du run sur `WS /orchestrator/observe` : aucun nouvel événement
backend. Une fonction pure (dernier événement, maintenant, question en
attente) → `actif | attente | blocage_suspecte | question`. Une question
d'agent en attente (ADR-025) prime : ce n'est pas un blocage. L'état s'affiche
comme une pastille dans la vue du run, avec les mots et couleurs de la
maquette `design/maquette/Bureau.dc.html` : « travaille » `blue`,
« silencieux » `zinc`, « question » `amber`, « figé ? » `red`.

## Critères d'acceptation
- [ ] Une fonction pure du frontend rend l'état, avec un test par seuil (29 s actif, 31 s attente, 181 s blocage suspecté)
- [ ] Un test montre qu'une question en attente rend `question` quel que soit le temps écoulé
- [ ] La vue du run affiche une pastille d'état, et un test React Testing Library le vérifie pour `blocage_suspecte`
- [ ] La pastille rend « travaille » en `blue`, « silencieux » en `zinc`, « question » en `amber` et « figé ? » en `red`, et un test le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/`

## Ce que ça ne fait pas
- Ne coupe aucun agent : `agent_silence_max_s` reste le seul arrêt.
