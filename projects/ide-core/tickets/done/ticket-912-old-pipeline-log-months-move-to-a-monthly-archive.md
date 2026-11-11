---
agent: codeur
created: 2026-11-10
depends_on: []
estimated_days: 1
id: ticket-912
plan: true
pr_number: null
priority: low
status: done
title: Old pipeline-log months move to a monthly archive
type: feat
---

# ticket-912 — Les vieux mois du journal du pipeline partent dans une archive mensuelle

## Objectif

Que `memory/pipeline-log.md` ne garde que les mois récents, le reste rangé
par mois, sans rien perdre.

## Contexte

Le journal d'ide-core fait 876 Ko (près de 9 000 lignes depuis septembre) et
ne fait que grandir. Aucun agent ne le lit en entier, mais chaque PR de run
le fusionne (union des lignes, `git_workspace/conflits.py`) et le dépôt le
transporte. Les autres projets suivent le même chemin (1 000 à 1 750 lignes).

Le journal est un artefact (`git_workspace/chemins.py`) : selon le mode du
projet (ADR-021, ADR-023), il est versionné ou exclu par
`.git/info/exclude`. Une archive doit suivre exactement le même sort.

## Solution proposée

- Un module `services/git_workspace/archive_journal.py` et un script
  `scripts/archiver_journal.py --projet <id|chemin> [--garder-mois 2]`.
- Les lignes datées d'un mois plus ancien que les `--garder-mois` derniers
  (mois courant compris) partent dans
  `memory/journal/pipeline-log-AAAA-MM.md`, ajoutées en fin de fichier si
  l'archive existe déjà. Une ligne sans date suit la ligne datée qui la
  précède.
- `memory/journal/` est déclaré comme artefact à côté du journal, pour être
  exclu ou versionné comme lui.
- Le script ne commite pas : il écrit, et dit combien de lignes ont été
  déplacées, par mois. Il se lance pendant le ménage mensuel, hors de toute
  file.

## Critères d'acceptation

- [ ] Un test vérifie qu'avec `garder_mois=2`, les lignes des mois plus
      anciens partent dans leur archive mensuelle et que le journal ne garde
      que les deux derniers mois.
- [ ] Un test vérifie qu'une ligne sans date suit la ligne datée qui la
      précède.
- [ ] Un test vérifie qu'une archive existante reçoit les nouvelles lignes
      à la fin, sans perdre les siennes.
- [ ] Un test vérifie que l'ensemble des lignes (journal plus archives) est
      identique avant et après l'archivage.
- [ ] `git_workspace/chemins.py` traite `memory/journal/` comme un artefact,
      et un test vérifie qu'il est exclu dans un projet en mode `local`.
- [ ] `scripts/archiver_journal.py` accepte `--projet` et `--garder-mois`,
      et un test l'exécute sur un dossier temporaire.

## Ce que ça ne fait pas

- Ne tourne pas tout seul, ni pendant un run : c'est un geste du ménage.
- Ne supprime aucune ligne.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un run qui écrit le journal pendant l'archivage : le script refuse de
tourner si un run est ouvert sur le projet (lecture de `RunLock` ou de
`/api/v1/usage/recent-runs`), ou le dit dans son plan.