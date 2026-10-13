---
agent: codeur
created: '2026-10-13'
depends_on: []
id: ticket-420
pr_number: 411
priority: high
status: done
title: 'Fin de file : la base locale reste en retard d''un commit et le journal reste
  sale après le merge du dernier ticket'
type: fix
---

## Signalement

- Projet source : affut
- Nature : bug
- Reçu le : 2026-10-13

## Description

File affut 043-051 (run 3a81b724), 2026-10-13. Après le merge de ticket-051 par le CIWatcher (PR #71, 13:27:14 UTC), le dépôt local reste sur main [behind 1], avec memory/pipeline-log.md modifié par la ligne « 13:27:20 UTC — [affut] ticket-051 PR #71 confiée au CIWatcher », écrite après le dernier commit. Même symptôme que le 2026-10-12 (ticket-042). ticket-406 réaligne la base au début du run SUIVANT, mais entre-temps les services du projet, relancés depuis l'arbre local (POST /projects/affut/services/start), servent du code périmé : le dernier ticket n'est pas actif. Repro : toute file en autonomy merge dont le dernier ticket est mergé en phase 2.

## Contexte

Contournement appliqué : git checkout -- memory/pipeline-log.md && git pull --ff-only, puis stop/start des services. Piste : quand le CIWatcher merge le dernier ticket d'une file et qu'aucun run n'occupe le projet, réaligner la base locale (ff-only) et commiter ou écarter la ligne de journal ; ou écrire cette ligne avant le commit de livraison.

## Solution retenue au triage (ide-core, 2026-10-13)

Même défaut vu sur curio et ide-core le même jour. Quand le `CIWatcher`
(`services/ci_watcher.py`) a mergé une PR (`_emettre_succes`) et que
**aucun run n'occupe le projet** (`RUN_REGISTRY.projet_occupe` faux) :
réaligner l'arbre local sur la base distante.

- Seulement si l'arbre est sur la branche de base et que ses seules
  modifications portent sur `memory/pipeline-log.md` : mettre de côté les
  lignes ajoutées du journal, `checkout --` du journal, `pull --ff-only`,
  puis réécrire les lignes qui n'y sont pas déjà.
- Tout autre état (autre branche, autre fichier modifié, échec du pull) : ne
  rien toucher, journaliser `realignement_ignore` avec la raison.
- Un échec n'altère jamais le résultat du merge (`merged` reste vrai).
- Le code est dans une fonction testable à part, appelée par le watcher.

## Critères d'acceptation

- [ ] Un test (dépôt git temporaire avec distant) vérifie qu'après un merge
      surveillé, sans run en cours, la base locale est à jour (`HEAD` égal à
      `origin/<base>`)
- [ ] Un test vérifie que la ligne de journal non commitée est conservée
      après le réalignement, et n'est pas dupliquée
- [ ] Un test vérifie qu'aucun réalignement n'a lieu quand un run occupe le
      projet
- [ ] Un test vérifie qu'aucun réalignement n'a lieu quand un autre fichier
      que le journal est modifié, et que l'arbre est laissé intact
- [ ] Un test vérifie qu'un échec du `pull` laisse `merged` à vrai