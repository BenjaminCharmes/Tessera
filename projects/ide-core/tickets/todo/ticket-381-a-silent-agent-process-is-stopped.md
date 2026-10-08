---
id: ticket-381
title: "An agent process that stays silent too long is stopped, instead of holding its run and its project forever"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-08
---

# ticket-381 — Un agent resté silencieux trop longtemps est arrêté

## Objectif

Qu'un processus d'agent figé (veille du PC, CLI bloqué) ne bloque plus son run
et le verrou de son projet indéfiniment.

## Contexte

`AgentSdkProvider._run` (`backend/src/tessera/services/providers/agent_sdk.py`)
parcourt `query(...)` sans aucune limite de temps. Si le `claude.exe` lancé
pour l'appel cesse d'émettre, l'appel attend pour toujours, le run aussi, et le
projet reste verrouillé.

Constaté deux fois :

- 2026-10-06 : après une veille du PC, la file ide-core figée 15 h ; il a
  fallu tuer le `claude.exe` du codeur à la main ;
- 2026-10-07/08 : la documentation du ticket-003 de vigie, repliée d'Ollama
  vers `agent_sdk` à 18:17:45 UTC, a figé son `claude.exe` (PID 40280)
  jusqu'au lendemain 07:00 ; tué à la main, le run a repris.

## Solution proposée

Borner l'attente **entre deux messages** du flux (pas la durée totale) à
`agent_silence_max_s` (réglage, 1200 s par défaut : un codeur peut lancer une
commande longue, comme la suite de tests, sans rien émettre). Au-delà :

1. fermer le flux, ce qui arrête le processus `claude.exe` ;
2. lever `ProviderIndisponible("agent silencieux depuis … s")`, pour que le
   repli ou l'échec fermé existant (ADR-037, ADR-039) prenne le relais ;
3. journaliser `agent_silencieux_arrete` avec le rôle et la durée.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_provider_agent_sdk.py` simule un flux qui émet un message puis plus rien, et vérifie que `_run` lève `ProviderIndisponible` après `agent_silence_max_s` (délai réduit pour le test)
- [ ] Un test de `backend/tests/test_provider_agent_sdk.py` vérifie que le flux est fermé (`aclose` appelé) quand le délai est dépassé
- [ ] Un test de `backend/tests/test_provider_agent_sdk.py` vérifie qu'un flux qui émet un message plus souvent que `agent_silence_max_s` aboutit normalement, même si sa durée totale dépasse ce délai
- [ ] `backend/src/tessera/config.py` déclare `agent_silence_max_s` avec 1200 par défaut

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Une commande d'agent qui reste muette plus de 20 min serait coupée : aucune
commande du pipeline n'en approche (suite de tests : environ 6 min).

## Ce que ça ne fait pas

- Ne détecte pas la veille du PC en tant que telle.
- Ne relance pas l'appel : le repli ou l'échec fermé existant s'en charge.
