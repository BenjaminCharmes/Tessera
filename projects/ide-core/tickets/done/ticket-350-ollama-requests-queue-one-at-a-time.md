---
agent: codeur
created: 2026-10-05
depends_on: []
estimated_days: 0.5
id: ticket-350
pr_number: null
priority: high
status: done
title: Ollama requests queue one at a time per server instead of competing for the
  model
type: fix
---

# ticket-350 — Les requêtes Ollama passent une à la fois par serveur

## Objectif

Que plusieurs runs qui appellent le même Ollama local ne se disputent plus le
modèle et la mémoire : chacun attend son tour, puis obtient une réponse à
pleine vitesse.

## Contexte

Le validateur et la documentation de plusieurs projets (serpent,
habit-tracker, homelab-monitor, repo-health, demineur, ide-core) passent par
`OllamaProvider` (`backend/src/tessera/services/providers/ollama.py`), avec
`qwen3-coder:30b` et `gpt-oss:20b`. Ollama traite les requêtes d'un modèle à
la suite et décharge l'un pour charger l'autre quand on les alterne. Avec
plusieurs files, les requêtes s'empilent côté serveur, et le délai de lecture
(`DELAI_LECTURE_S`, 300 s) court pendant cette attente invisible : des
validations de 330 s ont été relevées le 2026-10-05, et une requête peut
expirer sans avoir commencé.

Un `OllamaProvider` est construit par rôle (`provider_pour_role`) : un verrou
d'instance ne sérialise rien entre runs.

## Solution proposée

1. Un réglage `ollama_max_concurrent: int = 1` dans
   `backend/src/tessera/config.py` (0 ou moins : pas de borne).
2. Un registre de niveau module `base_url → asyncio.Semaphore`, créé
   paresseusement, partagé par tous les `OllamaProvider` du processus.
3. `complete` prend le créneau avant d'envoyer la requête et le rend après la
   réponse. `stream` le tient pendant tout le flux et le rend à sa fin, même
   si le consommateur s'arrête avant (générateur fermé, exception).
4. Le délai de lecture httpx ne commence qu'à l'envoi : l'attente du créneau
   n'est pas bornée par lui.

## Critères d'acceptation

- [ ] `config.py` déclare `ollama_max_concurrent` avec 1 pour défaut
- [ ] Un test de `test_provider_ollama.py` lance deux `complete` concurrents sur la même `base_url`
      avec un transport factice et vérifie qu'ils ne sont jamais en vol
      ensemble
- [ ] Un test montre que deux `base_url` distinctes ne se bloquent pas
      mutuellement
- [ ] Un test montre qu'un `stream` abandonné avant sa fin rend le créneau :
      un `complete` suivant aboutit
- [ ] Un test montre qu'une requête en erreur rend le créneau

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Un flux tenu longtemps bloque les autres rôles du même serveur : c'est voulu,
Ollama les aurait servis à la suite de toute façon.