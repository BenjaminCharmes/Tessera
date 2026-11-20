---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.2
id: ticket-937
pr_number: null
priority: high
status: done
title: "The git config fingerprint ignores branch sections, which execute nothing"
type: fix
---

# ticket-937 — L'empreinte de `.git/config` ignore les sections de branche

## Objectif

Qu'un `push -u`, le superviseur ou l'IDE qui écrivent l'upstream d'une branche
ne bloquent plus un run ide-core en cours.

## Contexte

Le ticket-933 prend l'empreinte des fichiers protégés, `.git/config` compris,
autour de chaque appel d'agent. Le 11/11 à 17:37 UTC, le run du ticket-912 a
été bloqué « fichier protégé modifié pendant un appel d'agent :
.git/config ». Le dépôt de Tessera porte ce jour-là des sections
`[branch "supervision-…"]` écrites par le superviseur (push avec upstream),
`[branch "ticket-936-…"]` écrite par un `push -u` d'une session humaine, et des
clés `vscode-merge-base` écrites par l'IDE. Aucune n'exécute rien ; toutes
changent le fichier entier.

Fait **à la main** : correctif isolé, qui bloquait la file du soir.

## Ce qui est fait

- `pipeline_empreinte.py` : `sans_sections_de_branche` retire les sections
  `[branch "…"]` du contenu haché de `config` et `config.worktree`. Toutes les
  autres sections restent dans l'empreinte, `[remote]` compris : une URL
  changée détournerait un push du backend.

## Critères d'acceptation

- [x] Un test vérifie qu'un upstream de branche et une clé
      `vscode-merge-base` ne changent pas l'empreinte.
- [x] Un test vérifie que `core.fsmonitor`, `core.hooksPath`, `diff.external`,
      `filter.*.clean` et `remote.origin.url` la changent toujours.
- [x] Les tests du ticket-933 passent.
