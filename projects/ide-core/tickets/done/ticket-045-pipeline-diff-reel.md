---
id: ticket-045
title: "Pipeline sur diff réel : branche par ticket, commits et isolation"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-044]
estimated_days: 3
created: 2026-09-14
---

# ticket-045 — Pipeline sur le diff réel

> **Note** : ticket rédigé rétrospectivement (2026-09-15), l'implémentation ayant
> démarré avant sa création. Voir la section « Process » plus bas.

## Objectif

Depuis [ticket-044](../done/ticket-044-agent-sdk-migration.md) le codeur écrit
réellement sur le disque. Le pipeline doit donc travailler sur **ce que le codeur a
écrit** — le diff git — et non plus sur la prose qu'il retourne ; et chaque run doit
être isolé sur sa propre branche, avec un commit à la clef.

## Contexte

Le reviewer, l'auditeur sécurité, le validateur et le doc-updater recevaient
`codeur_result.content` : un texte décrivant le travail. Ils validaient donc une
intention, pas une implémentation. Par ailleurs, rien ne committait : deux tickets
enchaînés en mode autonome se marchaient dessus dans un arbre de travail partagé.

## Solution livrée

### `GitWorkspaceService`

Un service dédié aux opérations git du pipeline, jamais appliqué à vibe-ide lui-même :

- `create_branch(ticket_id, slug)` — branche `ticket-XXX-slug`, idempotente,
  **forkée de la ref de base** et non de la branche du ticket précédent
- `current_diff()` — le diff réel, fichiers non suivis compris, en excluant la
  comptabilité interne de vibe-ide
- `commit_all(message)` — commit du travail du codeur, avec un **second commit
  séparé** pour la comptabilité (statuts de tickets, pipeline-log)
- `advance_base_ref()` — avance la base après une approbation
- `is_clean()` — filet de sécurité sur les fichiers **suivis** uniquement

### Orchestrateur

- Le diff réel alimente reviewer / sécurité / validateur / doc-updater, avec repli
  sur la prose du codeur si le diff est vide
- Commit sur **tous** les chemins de sortie : message typé du ticket si approuvé,
  message `chore: ... — unapproved work (...)` sinon
- Arbre sale au démarrage → le ticket passe en `blocked` (et non plus un refus qui
  bloquait toute la file en mode autonome)

## Décisions d'architecture

Voir **ADR-018** dans `memory/decisions.md` : isolation par branche, chaînage des
tickets approuvés, commits du travail non approuvé, périmètre de `is_clean`.

## Critères d'acceptation

- [x] Chaque run de pipeline crée (ou reprend) sa propre branche git
- [x] Le reviewer, l'auditeur sécurité et le validateur reçoivent le diff réel
- [x] La comptabilité vibe-ide est exclue du diff relu et du commit du ticket
- [x] Le message de commit utilise le type du ticket, pas un `feat:` codé en dur
- [x] Le travail non approuvé est commité sous un message Conventional Commits
- [x] Un ticket approuvé devient la base du ticket suivant (`advance_base_ref`)
- [x] Les messages de commit tiennent sur une seule ligne
- [x] Un fichier non suivi préexistant n'est jamais balayé dans le commit du ticket
- [x] `uv run mypy src/` passe sans erreur
- [x] La suite backend est verte sur Windows comme sur Linux

## Process

Ce ticket et [ticket-044](../done/ticket-044-agent-sdk-migration.md) ont été
implémentés sans fichier de ticket, en violation des règles 1 et 2 de `CLAUDE.md`.
Les deux fichiers ont été créés rétrospectivement le 2026-09-15 pour rétablir la
traçabilité. La cause : le travail a été piloté par des plans `docs/superpowers/`
au lieu du backlog de `projects/ide-core/`.

## Dépendances

`ticket-044` (les agents doivent écrire sur disque pour qu'un diff existe).

## Estimation

**3j**.
