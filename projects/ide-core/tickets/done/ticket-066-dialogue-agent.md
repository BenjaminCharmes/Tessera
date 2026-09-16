---
id: ticket-066
title: "Dialogue avec l'agent pendant un run — l'agent demande, l'utilisateur intervient"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-065]
estimated_days: 5
created: 2026-09-16
---

# ticket-066 — Dialogue bidirectionnel pendant un run

## Pourquoi

Le pipeline est un tuyau fermé : une fois lancé, il va du codeur au doc-updater
sans jamais rendre la main. Un agent qui bute sur une ambiguïté tranche seul, et
on ne découvre son hypothèse qu'au commit — souvent après qu'il a écrit le
mauvais code. Le WebSocket de `/stream/{project_id}` lit **un seul** message
entrant, la commande de démarrage, puis n'émet plus que des événements.

## Décision

Deux mécanismes, un seul transport.

**L'agent demande.** Un outil `ask_user(question)` est exposé aux agents du
pipeline. L'appel émet un événement `AGENT_QUESTION` et attend la réponse. Pas
de parsing de prose : contrairement au verdict du reviewer (ADR-009), le SDK
offre ici un mécanisme structuré.

**L'utilisateur intervient.** Les messages spontanés tombent dans une file
attachée au `PipelineRun`, vidée **entre deux tours d'agent** et préfixée au
prompt suivant. Pas d'interruption en plein token : on ne jette pas un tour
déjà payé pour gagner quelques secondes.

## Le piège

Un run en pause tient du travail **non commité**. ADR-018 fait reposer
l'enchaînement des tickets sur un arbre propre, et ADR-020 interdit déjà de
s'arrêter au milieu d'un ticket. Un agent qui attend une réponse jusqu'au matin
bloque la file.

D'où : au-delà d'un délai, l'agent **reprend seul sur une hypothèse qu'il
énonce**, et cette hypothèse part dans le rapport du run. En mode autonome, où
personne ne regarde, `ask_user` répond immédiatement sans attendre.

## Critères d'acceptation

- [x] Le WebSocket lit les messages entrants **en continu**, en parallèle de
      l'émission des événements
- [x] Un agent peut appeler `ask_user` ; le run se suspend et l'UI affiche la
      question
- [x] La réponse de l'utilisateur reprend le run là où il s'était arrêté
- [x] Un message spontané est injecté au tour d'agent suivant, pas plus tard
- [x] Au-delà du délai configuré, l'agent reprend sur une hypothèse **énoncée
      et consignée** dans le résultat du run
- [x] En mode autonome, `ask_user` ne bloque jamais
- [x] Un run qui se termine, question posée ou non, commite toujours (ADR-018)
- [x] Tests : suspension, reprise sur réponse, reprise sur délai, injection
      spontanée, mode autonome — sans appel LLM réel
- [x] ADR rédigé sur la reprise sur hypothèse

## Hors scope

- Interruption en plein tour d'agent
- Dialogue avec plusieurs runs simultanés depuis un même panneau

## Livré

- `DialogueChannel` : les deux sens, sans rien savoir du transport (`1599e2f`)
- WebSocket lu en continu pendant tout le run (`f6e27b5`)
- Outil `ask_user` exposé au codeur via un serveur MCP in-process (`7609f94`)
- Panneau de dialogue : question en attente, réponse, consigne (`ef07c3a`)
- ADR-025 sur la reprise sur hypothèse

## Portée assumée

`ask_user` n'est offert **qu'au codeur**. C'est le seul agent qui écrit du code
sur une hypothèse ; les autres jugent ce qui existe déjà, et un reviewer bloqué
dispose déjà de `CHANGES_REQUESTED` pour rendre la main. L'étendre plus tard
n'est qu'un `asker_for(run)` de plus au bon endroit.

L'interjection, elle, atteint **tous** les agents : elle transite par
`build_context`, où chaque tour construit son contexte.

## Non vérifié

Le trajet complet — un vrai agent décidant d'appeler `ask_user` pendant un run
réel — n'a pas été exercé : il demande un appel LLM facturé. Tout ce qui
l'entoure l'est : l'outil, son intégration dans les options du SDK, le canal,
le WebSocket et l'UI.
