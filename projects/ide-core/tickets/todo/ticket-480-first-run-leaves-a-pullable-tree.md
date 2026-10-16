---
id: ticket-480
title: "After a run, the base branch pulls cleanly and leftover untracked files are reported"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
plan: true
created: 2026-10-16
---

# ticket-480 — Un pull propre après le premier run d'un projet

## Objectif

Après la livraison d'un run, `git pull` sur la base passe sans geste à la
main, et les fichiers non suivis qu'un run laisse sont signalés.

## Contexte

souhaito, 16/10 :
1. Après le merge de la PR #1 (premier run du projet),
   `memory/pipeline-log.md` était non suivi dans l'arbre local mais suivi
   dans la PR : `git pull` refusait d'écraser le fichier, et la session a dû
   mettre les lignes de côté puis les réinjecter. Le ticket-457 traite un
   journal modifié, pas un journal non suivi que le merge apporte.
2. Après le run bloqué du 002, `src/generated/` (client Prisma) est resté
   non suivi dans l'arbre de la base.

## Solution proposée

- Au retour sur la base et au réalignement (tickets 378 et 457) : si
  `memory/pipeline-log.md` est non suivi localement et présent sur la base
  distante, mettre ses lignes de côté, réaligner, puis réappliquer les
  lignes absentes (union, sans doublon), comme pour un journal modifié.
- Lister les fichiers non suivis et non ignorés restés après le run, et
  écrire une ligne au journal : « fichiers non suivis laissés par le run :
  … (à ignorer dans .gitignore ?) ». Ne pas les supprimer.

## Critères d'acceptation

- [ ] Un test part d'un journal non suivi localement et suivi sur la base
      distante, et vérifie que le réalignement aboutit avec les lignes
      locales conservées une seule fois
- [ ] Un test vérifie la ligne de journal qui liste un fichier non suivi
      laissé par le run, et que ce fichier n'est pas supprimé
