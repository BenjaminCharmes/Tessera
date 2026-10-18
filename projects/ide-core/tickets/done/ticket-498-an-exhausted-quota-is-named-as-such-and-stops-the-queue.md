---
agent: codeur
created: 2026-10-17
depends_on: []
estimated_days: 1
id: ticket-498
plan: true
pr_number: null
priority: medium
status: done
title: An agent call cut by an exhausted subscription quota is logged as such, and
  stops the queue instead of blocking the ticket
type: fix
---

# ticket-498 — Un quota épuisé se dit « quota épuisé », pas « ProcessError »

## Objectif

Quand l'appel d'un agent échoue parce que le quota d'abonnement est épuisé,
`pipeline-log.md` le dit en ces termes, avec l'heure de reprise si elle est
connue, et la file s'arrête proprement au lieu de compter un échec du ticket.

## Contexte

Le 16/10 à 18:55 UTC puis le 17/10 à 07:38 UTC, plusieurs runs (ide-core,
Kadoomi, Devinoo) sont tombés dans la même minute sur
« ProcessError: Command failed with exit code 1 … Check stderr output for
details », stderr vide. C'était le quota hebdomadaire, puis celui de la
session. Les sessions de projet ont cherché un crash de `claude.exe` ou une
coupure du backend avant de comprendre.

`quota_tracker.py` (ticket-054) suit déjà la fenêtre de quota que le SDK
signale (`snapshot_from_rate_limit`, statut `rejected`, `is_exhausted`), et
l'orchestrateur sait écrire « run interrompu : quota d'abonnement à … » entre
deux tickets. Il manque le cas où le quota tombe **pendant** un appel.

## Solution proposée

1. Une fonction pure qui, à partir de l'exception d'un appel d'agent et du
   dernier `QuotaSnapshot`, dit si l'échec vient du quota : snapshot
   `rejected`, ou texte d'erreur évoquant une limite d'usage (« usage limit »,
   « rate limit », « allowance »), ou `ProcessError` à stderr vide alors que le
   dernier snapshot était `allowed_warning`.
2. Dans ce cas : ligne de journal `quota épuisé — reprise vers <HH:MM UTC>`
   (heure tirée du snapshot, sinon « heure inconnue »), le ticket revient en
   `todo` sur sa branche (travail commité comme aujourd'hui, ADR-037), et la
   file s'arrête avec `file interrompue : quota épuisé`.
3. Tout autre `ProcessError` garde le traitement actuel.

## Ce que ça ne fait pas

- Ne relance pas la file seule à la reprise du quota.
- Ne change pas les seuils du mode autonome (ADR-020).

## Critères d'acceptation

- [ ] Un test vérifie qu'un `ProcessError` avec un dernier snapshot `rejected`
      est reconnu comme quota épuisé
- [ ] Un test vérifie qu'un message d'erreur contenant « usage limit » est
      reconnu, et qu'un `ProcessError` ordinaire avec un snapshot `allowed`
      ne l'est pas
- [ ] Un test vérifie que la ligne de journal contient « quota épuisé » et
      l'heure de reprise du snapshot
- [ ] Un test vérifie qu'un quota épuisé en cours de ticket arrête la file
      avec `file interrompue : quota épuisé` et remet le ticket en `todo`