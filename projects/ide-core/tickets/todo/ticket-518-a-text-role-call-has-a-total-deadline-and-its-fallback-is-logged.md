---
id: ticket-518
title: "A validator, security or documentation call has a total deadline, and switching to its fallback is written in the pipeline log"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
plan: true
created: 2026-10-19
---

# ticket-518 — Un appel de rôle texte a une durée totale bornée, et son repli se voit

## Objectif
Qu'un validateur, un audit ou une documentation ne puisse plus geler une file
plus d'une durée connue, et que le passage au provider de repli soit visible
dans `memory/pipeline-log.md`.

## Contexte
Le 19/10, Kadoomi ticket-029 (run 72932054), tour 3 : reviewer terminé à
15:09:56 UTC, puis plus rien jusqu'à 16:32:12, quand le pipeline a écrit
« validateur: CHANGES_REQUESTED — Validation indisponible : agent silencieux
depuis 1200 s (5007671ms) » et a bloqué le ticket. 83 minutes de file perdues.

Le validateur de Kadoomi est déclaré `ollama` / `qwen3-coder:30b`, avec en
repli `agent_sdk` / `claude-haiku-4-5`. Le message « agent silencieux » vient
du chien de garde d'`agent_sdk.py`, donc du **repli** : l'appel Ollama a d'abord
duré environ 3 800 s, avant d'échouer ou d'expirer, puis Haiku est resté
silencieux 1 200 s. Rien dans le journal du pipeline ne dit que le repli a
joué : l'événement `provider_fallback` (`providers/repli.py`) ne laisse
aucune ligne dans `pipeline-log.md`.

Les bornes actuelles sont toutes relatives :
- Ollama : `DELAI_LECTURE_S = 300` entre deux morceaux de réponse, plus une
  attente de créneau (`ollama.py`, ligne 75). Une génération qui continue
  d'émettre, ou une longue file d'attente de créneaux, n'a pas de fin.
- `agent_sdk` : 1 200 s de silence. Un flux qui continue d'émettre n'a pas de
  fin non plus.
Les logs du backend partent sur sa console : impossible de départager, après
coup, l'attente de créneau, une génération sans fin ou un CLI figé.

## Solution proposée
1. Une durée totale maximale par appel pour les rôles texte (validateur,
   securite, doc-technique, doc-fonctionnelle), attente de créneau comprise,
   réglable (`LLM_DUREE_MAX_ROLE_TEXTE_S`, défaut 900 s). Dépassée, elle
   lève `ProviderIndisponible` : le repli joue, et un repli qui dépasse aussi
   échoue fermé (ADR-039).
2. Chaque passage au repli écrit
   `[ticket-XXX] <rôle>: repli vers <provider>/<modèle> — <cause>` dans le
   journal du pipeline.
3. Diagnostic (tour de plan) : dire pourquoi l'appel Ollama a pu durer
   environ 3 800 s. Attente de créneau, génération qui ne s'arrête pas
   (`num_predict` envoyé = `max_tokens` ?), ou autre. Corriger ce qui
   l'explique.

## Critères d'acceptation
- [ ] Un test vérifie qu'un appel Ollama qui continue d'émettre au-delà de la durée maximale lève `ProviderIndisponible`
- [ ] Un test vérifie que l'attente d'un créneau Ollama compte dans cette durée maximale
- [ ] Un test vérifie qu'un appel `agent_sdk` d'un rôle texte qui continue d'émettre au-delà de la durée maximale lève `ProviderIndisponible`
- [ ] Un test vérifie qu'un passage au repli écrit la ligne `<rôle>: repli vers …` dans `pipeline-log.md`
- [ ] Le plan nomme la cause des 3 800 s, ou les hypothèses écartées avec leur preuve
- [ ] Les tests existants de `providers/` passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Un jour.

## Risques
Une borne trop courte couperait un validateur lent mais sain : la régler
au-dessus du plus long appel observé dans `agent_calls` sur 7 jours.
