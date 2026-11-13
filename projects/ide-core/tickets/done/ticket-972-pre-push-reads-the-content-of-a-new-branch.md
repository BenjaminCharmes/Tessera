---
agent: codeur
created: 2026-11-13
depends_on: []
id: ticket-972
priority: critical
status: done
title: "The pre-push hook reads the content of a new branch, not only its messages"
type: fix
---

# ticket-972 — Le hook pre-push lit le contenu d'une branche neuve, pas seulement ses messages

## Signalement

- Source : agent:codeur@ticket-968
- Nature : bug, catégorie outil_casse, composant garde_secrets

## Contexte

`scripts/hooks/pre-push`, `_get_diff_lines` : pour une branche neuve
(`remote_sha` nul), la commande était `git log -p --not --remotes
<local_sha>`. `--not` s'applique à toutes les révisions qui le suivent, donc
aussi à `local_sha` : le diff était vide. Une branche neuve, c'est-à-dire tout
push à la main d'une branche de ticket, n'était contrôlée que sur ses
messages et ses auteurs, jamais sur son contenu (ADR-048, ADR-050).

## Correctif

`git log -p <local_sha> --not --remotes`. Le hook installé dans
`.git/hooks/` de Tessera est une copie (`make install-hooks`) : à recopier
après le merge.

## Critères d'acceptation

- [x] Un test sur un vrai dépôt : le diff d'une branche neuve contient la
      ligne ajoutée par son commit.
- [x] Les tests existants du hook passent sans changement.

## Ce que ça ne fait pas

- Fait à la main : le hook est protégé en écriture pour les agents.
