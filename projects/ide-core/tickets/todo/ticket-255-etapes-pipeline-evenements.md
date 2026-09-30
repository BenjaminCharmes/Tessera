---
id: ticket-255
title: "Every pipeline stage announces its start, and the run snapshot names it"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-30
---

# ticket-255 — Chaque étape du pipeline annonce son début

## Objectif

Qu'un observateur sache à tout instant quelle étape d'un run travaille, y
compris celles qui ne sont pas des agents conversationnels.

## Contexte

Constaté en réel le 2026-09-30 sur le ticket-253 : après `reviewer terminé`, le
run a tourné plusieurs minutes sans rien émettre. L'écran semblait figé.

Les étapes n'annoncent pas toutes leur début :

| Étape | Début | Fin |
|---|---|---|
| audit sécurité | `security_audit_started` | `security_audit_done` |
| validation | — | `validation_done` |
| documentation (ADR-035) | — | `doc_updated`, ou `documentation_failed` |
| livraison (ADR-030) | — | `livraison_done` |

`run_validation` (`services/pipeline_stages.py`), `_documenter_le_run` et
l'appel de livraison dans `run_pipeline` (`services/orchestrator.py`)
travaillent donc en silence, parfois plusieurs minutes (le validateur lit chaque
critère en entier ; la livraison attend une CI bornée).

L'instantané du registre (`RunActif.en_dict`, `services/run_registry.py`) porte
`agent` mais aucune étape. Un observateur arrivé en cours de validation ne voit
qu'un reviewer terminé (ticket-163, ticket-182 : l'état décide, les événements
enrichissent).

Ce ticket ne touche **que le backend**. L'affichage est le ticket-256.

## Solution proposée

- Ajouter à `EventType` (`services/pipeline_events.py`) : `VALIDATION_STARTED`,
  `DOCUMENTATION_STARTED`, `LIVRAISON_STARTED`, avec un commentaire de ligne
  comme leurs voisins.
- Les émettre au début de l'étape correspondante, **seulement si l'étape tourne
  vraiment** : pas de `validation_started` quand `orch._validator is None`,
  pas de `documentation_started` sans documenter, pas de `livraison_started`
  sur un run non approuvé.
- Ajouter un champ `etape: str | None` à `RunActif`, exposé dans `en_dict()`.
  Valeurs : `production`, `tests`, `securite`, `revue`, `validation`,
  `documentation`, `livraison`. Il se met à jour là où le registre suit déjà
  les événements d'un run (même mécanisme que `agent`).
- Un émetteur qui lève n'interrompt pas le run (ADR-038) : réutiliser `emit`,
  qui le garantit déjà.
- Ajouter les trois valeurs à l'union `OrchestratorEventType` de
  `frontend/src/types/api.ts`, pour que le contrat reste aligné ; rien d'autre
  côté frontend.

## Critères d'acceptation

- [ ] `EventType` contient `VALIDATION_STARTED`, `DOCUMENTATION_STARTED` et
      `LIVRAISON_STARTED`, et `frontend/src/types/api.ts` contient leurs trois
      valeurs.
- [ ] Un test montre qu'un run avec validateur émet `validation_started` avant
      `validation_done`, et qu'un run sans validateur n'émet pas
      `validation_started`.
- [ ] Un test montre que `documentation_started` précède `doc_updated` (ou
      `documentation_failed`) sur un run approuvé avec documenteur.
- [ ] Un test montre que `livraison_started` précède `livraison_done` sur un run
      approuvé, et qu'un run non approuvé n'émet ni l'un ni l'autre.
- [ ] Un test montre que `RunActif.en_dict()` contient la clef `etape`, et
      qu'elle vaut `validation` après un événement `validation_started`.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

- Les tests qui comparent la séquence exacte d'événements d'un run vont voir
  apparaître les nouveaux : les adapter, sans affaiblir ce qu'ils vérifient.
- Ne pas émettre depuis `LivraisonService` lui-même : l'événement part de
  l'orchestrateur, là où `livraison_done` part déjà.
