---
id: ticket-139
title: "Un tour de chat qui écrit doit prendre le verrou du projet"
type: fix
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-139 — Un tour de chat qui écrit doit prendre le verrou

## Objectif

Empêcher un tour de chat d'écrire dans l'arbre d'un projet pendant qu'un run
y travaille.

## Contexte

**Reproduit.** Sur un projet marqué occupé par un run, un tour de chat
démarre quand même : la WebSocket répond `{"type": "start"}` au lieu de
refuser.

Le verrou n'est pris qu'à un seul endroit du chat — `POST /chat/run`
(`routers/chat.py:246`), qui lance un pipeline. Le tour conversationnel passe
par `WS /{project_id}/chat` → `_handle_turn`, et n'en prend aucun.

Or ce tour **écrit** : `ChatService._commit_if_written` crée une branche
`chat-<horodatage>` et commite dès que l'arbre n'est pas propre (ADR-019).
Pendant un run, ce `create_branch` fait un checkout sous le codeur — la panne
exacte qu'ADR-038 décrit pour deux runs, prise par l'autre porte.

ADR-038 annonce pourtant un verrou « partagé par tous les points d'entrée —
run unique, file, autonome, chat ». Sa décision parle de refuser « un second
**run** », et un tour de chat n'en est pas un au sens strict : c'est cet écart
entre l'intention et la lettre qui a laissé le trou.

## Solution proposée

`_handle_turn` acquiert `RUN_LOCK` pour la durée du tour, et répond
`{"type": "error"}` en nommant ce qui occupe le projet lorsqu'il est pris.
La réciproque vient gratuitement : le verrou étant partagé, un run lancé
pendant un tour de chat est refusé.

Tenir le verrou pendant tout le tour est délibéré : c'est la durée pendant
laquelle l'agent peut écrire.

Le libellé passé au verrou est `chat`, pour qu'un run refusé dise ce qui
l'occupe plutôt qu'un identifiant vide.

**À vérifier pendant l'implémentation** : un tour purement conversationnel
n'écrit rien et ne crée pas de branche. Le bloquer quand même est-il le bon
compromis ? Oui par défaut — on ne sait pas d'avance si l'agent va écrire, et
se tromper dans ce sens coûte une attente, pas un arbre corrompu.

## Critères d'acceptation

- [ ] Un test vérifie qu'un tour de chat sur un projet occupé par un run
      reçoit `{"type": "error"}` nommant ce qui l'occupe
- [ ] Un test vérifie qu'un tour de chat passe normalement sur un projet libre
- [ ] Un test vérifie qu'un `POST /orchestrator/run` est refusé (409) pendant
      un tour de chat
- [ ] Un test vérifie que le verrou est relâché après le tour, y compris quand
      celui-ci lève
- [ ] La correction n'ajoute pas de second verrou : `RUN_LOCK` reste unique
- [ ] `uv run pytest` et `uv run mypy src/` passent

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un verrou tenu et jamais relâché bloque le projet jusqu'au redémarrage du
backend : le `finally` de `RunRegistry.acquire` couvre ce cas, et le test qui
lève dans le tour est ce qui le vérifie.

Une conversation longue tient le verrou longtemps. C'est assumé — mais si ça
gêne à l'usage, le vrai correctif serait de ne verrouiller qu'à la première
écriture, ce qui demande un signal que `ChatService` n'émet pas aujourd'hui.
