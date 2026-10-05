---
id: ticket-345
title: "The planner reads any valid JSON answer, and keeps the raw answer when it cannot"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-345 — Le planificateur lit toute réponse JSON valide, et garde la réponse brute quand il ne peut pas

## Objectif

« Planifier une évolution » ne renvoie plus 502 sur une réponse JSON valide,
et quand la réponse est vraiment illisible, elle est conservée en entier pour
qu'on puisse dire pourquoi.

## Contexte

Le 2026-10-05, sur le projet `serpent`, une demande de 8 à 12 tickets a
produit 15 363 tokens en 120 s (`planner_call` dans `tessera.log`) puis un
502 : « Le planificateur n'a pas retourné un JSON valide ». La réponse n'était
pas tronquée — `AgentSDKProvider` ignore `max_tokens`. Relancée avec 6 à 8
tickets et la consigne « ni guillemets droits, ni accolades, ni bloc de
code », elle est passée.

`extract_json` (`backend/src/tessera/utils/json_extract.py`) a deux faiblesses :

- la regex `\{.*?\}` s'arrête au premier `}` suivi de trois backticks, même
  à l'intérieur d'une chaîne ;
- le repli compte les accolades **sans tenir compte des chaînes** : une
  accolade dans un texte de ticket fausse le compte, et la première erreur de
  décodage rend `None`.

Et `planner.py` ne garde que `raw[:200]` : la cause exacte de l'échec du
2026-10-05 est perdue.

## Solution proposée

1. `extract_json` essaie `json.JSONDecoder().raw_decode` à partir de chaque
   `{` du texte, dans l'ordre, et rend le premier objet `dict` décodé. Le
   décodeur connaît les chaînes : plus besoin de compter les accolades. Le
   bloc entre backticks reste essayé en premier.
2. Sur échec, `PlannerService.plan` journalise la réponse brute **complète**
   (`planner_reponse_illisible`, champ `raw`) avant de lever. Le message de
   l'erreur HTTP peut rester court.

## Critères d'acceptation

- [ ] Un test de `extract_json` décode un objet dont une chaîne contient `}` suivi de trois backticks
- [ ] Un test de `extract_json` décode un objet dont une chaîne contient une accolade ouvrante seule
- [ ] Un test de `extract_json` décode un objet précédé d'un texte qui contient lui-même `{` non JSON
- [ ] Un test de `extract_json` rend `None` sur un objet tronqué
- [ ] Les tests existants de `extract_json` et de `test_planner.py` passent sans être modifiés
- [ ] Un test de `PlannerService` vérifie qu'une réponse illisible produit un log `planner_reponse_illisible` contenant la réponse entière

## Ce que ça ne fait pas

- Pas de réparation de JSON invalide (guillemet non échappé, virgule en trop) : un JSON faux reste un échec, mais un échec qu'on peut lire.
- Pas de relance automatique de l'appel.
- Ne touche pas la limite de 2000 caractères du champ de description.

## Dépendances

Aucune.

## Risques

`extract_json` sert aussi à `agent_creator`, `project_analyzer`,
`project_creator` et `security_auditor`. Ce qui décodait hier doit décoder
pareil : c'est ce que garde le critère sur les tests existants.
