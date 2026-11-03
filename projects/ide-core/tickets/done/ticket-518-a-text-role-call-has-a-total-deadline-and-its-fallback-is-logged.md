---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 1
id: ticket-518
plan: true
pr_number: 575
priority: high
status: done
title: A validator, security or documentation call has a total deadline, and switching
  to its fallback is written in the pipeline log
type: fix
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
## Diagnostic des 3 800 s

**La cause n'est pas nommée.** Trois hypothèses sont écartées, preuve dans le
code ; deux restent ouvertes.

Écartées :
- **Attente de créneau.** `ollama.py:74` plafonne l'attente à
  `ollama_slot_wait_s` (30 s) et refuse sans requête au-delà. Elle ne peut pas
  expliquer des milliers de secondes.
- **Génération sans fin.** `validator.py:25` fixe `_MAX_TOKENS = 2048` et
  l'appel est `complete` (`validator.py:113`), donc non-stream : `ollama.py:281`
  envoie `num_predict = max_tokens`, et le délai de lecture httpx
  (`DELAI_LECTURE_S = 300`, `ollama.py:33`) couvre toute la génération, faute de
  morceau intermédiaire. Un `complete` Ollama ne dépasse donc pas environ 335 s.
- **Veille de la machine.** L'écart du journal, de 15:09:56 à 16:32:12
  (4 936 s), correspond à la durée mesurée du validateur (5 007 s) : l'horloge
  n'a pas été suspendue. Preuve indirecte.

Restent ouvertes : le délai httpx n'a pas coupé, ou le temps est passé hors de
l'appel provider. Aucune ligne n'est écrite au démarrage de l'appel Ollama ni
au passage au repli, et un échec n'écrit rien dans `agent_calls`
(`enregistrant.py` n'enregistre qu'après un appel réussi).

Ce que le correctif garantit : `borner` enveloppe la vérification du modèle, le
créneau et la requête. Quelle que soit la cause, un appel Ollama d'un rôle
texte s'arrête à 900 s, le repli aussi, et le passage au repli laisse une ligne
dans `pipeline-log.md`. Si l'incident revient, la ligne de repli dira que
l'appel principal a échoué et pourquoi ; tracer début et fin de chaque appel
provider dépasse ce ticket.

## Durée maximale observée (risque du ticket)

Mesure en lecture seule sur `agent_calls.duration_ms`, 7 derniers jours, base
`backend/tessera.db` : validateur 517 s (333 appels), securite 240 s (343),
doc-technique 212 s (310), doc-fonctionnelle 265 s (314). Tous sous les 900 s
de la borne par défaut. La base lue est celle du dossier `backend/` : elle peut
différer de la base de production.