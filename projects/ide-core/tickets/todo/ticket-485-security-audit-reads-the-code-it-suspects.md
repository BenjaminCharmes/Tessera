---
id: ticket-485
title: "The security audit can read the project's code before it blocks on a sink outside the diff"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
plan: true
created: 2026-10-16
---

# ticket-485 — L'audit de sécurité lit le code qu'il soupçonne

## Objectif

Avant de bloquer un run sur une faille qui passerait par du code absent du
diff, l'audit de sécurité peut lire ce code, au lieu de supposer que la
protection manque.

## Contexte

Deux faux positifs le 16/10, de même cause :
- ide-core, ticket-458 : BLOCK « path traversal » sur `pipeline_log_path`,
  un chemin construit par Tessera lui-même, que le diff ne faisait que
  réutiliser ;
- kadoomi, ticket-012 : BLOCK « SSRF » parce qu'une URL arrivait par une
  nouvelle source jusqu'à `previewLink()`. L'auditeur écrivait que la
  fonction « ferait probablement » une requête sans garde, alors que
  `safeFetch` (hors diff) refuse déjà les IP privées à chaque saut.

`backend/src/tessera/services/security_auditor.py` envoie le diff seul par
`provider.complete`, sans aucun outil : l'auditeur ne peut rien vérifier.
Le reviewer, lui, a des outils de relecture (`OUTILS_DE_RELECTURE` :
`Read`, `Glob`, `Grep`, dans `backend/src/tessera/services/agent_runner.py`).

## Solution proposée

- L'audit tourne avec les outils de relecture, limités au projet comme ceux
  du reviewer (ADR-031) ; aucun outil d'écriture ni `Bash`.
- Le prompt de l'auditeur (`agents/prompts/securite.md`) lui demande, avant
  un BLOCK sur un flux qui atteint du code hors diff, de lire ce code et de
  citer dans son verdict la ligne qui manque ou la garde trouvée.
- Le verdict reste échoué fermé (ADR-039) : outil indisponible ou réponse
  illisible donne toujours BLOCK.

## Critères d'acceptation

- [ ] Un test vérifie que l'audit est lancé avec `Read`, `Glob` et `Grep`,
      et sans `Write`, `Edit` ni `Bash`
- [ ] Un test vérifie que les chemins lisibles par l'audit sont bornés au
      projet
- [ ] `agents/prompts/securite.md` contient la consigne de lire le code hors
      diff avant un BLOCK et de citer la garde ou son absence
- [ ] Un test vérifie qu'une erreur du provider donne toujours BLOCK
