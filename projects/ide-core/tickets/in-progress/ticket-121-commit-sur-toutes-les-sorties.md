---
id: ticket-121
title: "Commiter sur toutes les sorties, tolérer une socket morte, un run à la fois par projet"
type: fix
status: in-progress
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-22
---

# ticket-121 — Commiter sur toutes les sorties, tolérer une socket morte, un run à la fois par projet

## Objectif

Tenir ADR-018 et ADR-037 sur tous les chemins de sortie du pipeline, pas
seulement le chemin approuvé, et empêcher deux runs de se marcher dessus sur
un même projet.

## Contexte

- `commit_work` lève `CommitFailed` ; seul `finish_approved` l'attrape.
  `finish_security_block`, `finish_stopped`, `finish_rounds_exhausted` la
  laissent remonter à `_run_pipeline`, qui appelle `finish_interrupted`, qui
  rappelle `commit_work`, qui relève → 500 FastAPI, arbre sale, run jamais
  clos en base (le côté WS n'attrape que `ValueError`).
- En mode single, `send_event` avale les erreurs de socket. En mode file et
  autonome, `send_queue_event` / `send_event_autonomous` ne le font pas : un
  onglet fermé en plein tour interrompt le run **avant** le commit.
- `RunLock` n'existe que pour `/chat/run`. Deux `POST /orchestrator/run` sur
  le même projet passent `ensure_clean_tree` puis le second `create_branch`
  fait un checkout sous le premier codeur.
- `run_queue`, `run_autonomous` et `/chat/run` appellent `run_pipeline` sans
  `run_id` : aucun coût persisté dans `agent_calls`, aucun `create_run` /
  `finish_run`. La ventilation des coûts ignore les modes qui coûtent le plus.

## Solution proposée

1. Un seul point de sortie : `commit_work` attrapé dans une fonction commune
   utilisée par les quatre `finish_*` ; un `CommitFailed` rend `blocked` avec
   `arret="commit_failed: …"`. `finish_interrupted` ne relance jamais une
   exception de commit.
2. `send_event` tolérant partagé par les trois modes (une seule fonction,
   la version single existe déjà).
3. `RunLock` étendu à `/orchestrator/run`, `/run-queue`, `/run-autonomous`
   et la WS, clé = `project_id`. Second appel → 409 avec le ticket en cours.
4. `run_queue` et `run_autonomous` créent un `run_id` par ticket
   (`create_run` / `finish_run`) et le passent à `run_pipeline` ; `/chat/run`
   aussi. Le côté WS n'attrape plus seulement `ValueError` : toute exception
   ferme le run en base.

Hors périmètre : reprise d'un run interrompu, verrou inter-process, verdicts
et logger (ticket-122).

## Critères d'acceptation

- [x] Tests : `CommitFailed` sur `security_block`, `stopped`,
      `rounds_exhausted` et `interrupted` donne un `PipelineResult` `blocked`
      avec `arret` renseigné, jamais une exception
- [x] Test : un `on_event` qui lève en mode file n'empêche pas le commit
- [x] Test : deux runs simultanés sur le même projet → le second reçoit 409 ;
      deux projets différents → les deux passent
- [x] Test : `run_queue` sur deux tickets écrit deux lignes dans `runs` et
      leurs `agent_calls` portent le `run_id`
- [x] `uv run pytest -q` et `uv run mypy src/` verts

## Ce que ça ne fait pas

- **Le verrou est en mémoire du process.** Deux backends sur un même dépôt
  ne se voient pas ; un redémarrage libère tout. Suffisant pour un serveur
  local, documenté dans ADR-038.
- **Pas de reprise d'un run interrompu.** Le travail est commité, l'arbre est
  propre, mais rien ne relance le ticket : c'est à l'utilisateur.
- **Les événements des modes file et autonome ne sont pas persistés.** Chaque
  ticket a bien sa ligne dans `runs` et ses `agent_calls`, mais l'émetteur
  WebSocket n'a pas de `run_id` par ticket à leur rattacher ; seul le run
  unique garde son fil d'événements.
- **La tolérance de l'émetteur vit dans l'orchestrateur**, pas seulement dans
  le routeur : un `on_event` programmatique qui lève est journalisé et
  ignoré. Un appelant qui veut voir cette erreur doit la gérer lui-même.
- **Le verrou refuse, il ne fait pas la queue.** Un second clic reçoit 409
  avec le ticket en cours ; il ne sera pas rejoué à la fin du premier.
- Verdicts, auditeur sécurité, logger et sujets de commit : ticket-122.

## Dépendances
Aucune.

## Estimation
2 jours.

## Risques
Le verrou est en mémoire du process : documenté, suffit pour un serveur local.
