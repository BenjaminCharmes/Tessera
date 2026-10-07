---
id: ticket-380
title: "A saturated or timed-out Ollama falls back at once instead of making every role wait minutes"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-07
---

# ticket-380 — Un Ollama saturé ou trop lent bascule tout de suite sur le repli

## Objectif

Qu'un rôle confié à Ollama ne fasse plus attendre un run plusieurs minutes
avant de basculer de toute façon sur son repli.

## Contexte

`backend/src/tessera/services/providers/ollama.py` prend un créneau par
serveur (`settings.ollama_max_concurrent`, 1 par défaut, ticket-350) et
attend ce créneau **sans limite**, puis applique un délai de lecture de
`DELAI_LECTURE_S` = 300 s.

Constaté le 2026-10-07, avec quatre files en parallèle (ide-core, affut,
carriere, vigie) : le serveur répond (`/api/tags` en 0,8 s), mais les vraies
requêtes dépassent les 300 s. Chaque appel finit en `provider_fallback` vers
`agent_sdk`, avec le message vide « Ollama injoignable : » (un dépassement de
délai `httpx` n'a pas de texte). Chaque rôle attend donc la file du créneau,
puis 300 s, puis le repli :

- vigie ticket-002 : « documentation: 0 fichier(s) (1157438ms) », 19 min ;
- affut : documentation entre 345 et 1027 s par ticket ;
- le verrou du projet reste tenu pendant tout ce temps.

Signalé par la session qui pilote vigie.

## Solution proposée

1. **Attente de créneau bornée** : au-delà de `ollama_slot_wait_s` (réglage,
   30 s par défaut), lever `ProviderIndisponible` sans envoyer la requête : le
   repli prend le relais.
2. **Disjoncteur par serveur** : après un dépassement du délai de lecture, ce
   serveur est marqué lent pendant `ollama_cooldown_s` (réglage, 600 s par
   défaut) ; pendant ce temps, tout appel lève `ProviderIndisponible` aussitôt,
   sans requête. À l'issue, un appel est de nouveau tenté.
3. **Message clair** : un dépassement de délai produit
   « Ollama : délai dépassé (… s) », distinct d'une connexion refusée.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_provider_ollama.py` occupe le créneau et vérifie qu'un second appel lève `ProviderIndisponible` après `ollama_slot_wait_s`, sans requête HTTP
- [ ] Un test de `backend/tests/test_provider_ollama.py` simule un dépassement du délai de lecture, puis vérifie que l'appel suivant lève `ProviderIndisponible` aussitôt, sans requête HTTP, tant que `ollama_cooldown_s` n'est pas écoulé (horloge simulée)
- [ ] Un test de `backend/tests/test_provider_ollama.py` vérifie qu'une fois `ollama_cooldown_s` écoulé, un appel envoie de nouveau une requête
- [ ] Un test de `backend/tests/test_provider_ollama.py` vérifie que le message d'un dépassement de délai contient « délai dépassé »
- [ ] `backend/src/tessera/config.py` déclare `ollama_slot_wait_s` et `ollama_cooldown_s`

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Pendant le refroidissement, les rôles Ollama passent par leur repli, payant
s'il est sur `agent_sdk` : c'est déjà ce qui arrive aujourd'hui, en minutes
d'attente en plus.

## Ce que ça ne fait pas

- Ne change pas les modèles ni les fournisseurs déclarés par les projets.
- Ne raccourcit pas le délai de lecture d'un appel réellement en cours.
