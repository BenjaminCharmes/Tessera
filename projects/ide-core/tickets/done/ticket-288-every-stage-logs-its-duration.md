---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 1
id: ticket-288
pr_number: 175
priority: high
status: done
title: Every pipeline stage writes its duration to the pipeline log, delivery steps
  included
type: chore
---

# ticket-288 — Chaque étape du pipeline journalise sa durée

## Objectif

Savoir où passe le temps d'un ticket à la lecture de `memory/pipeline-log.md`,
sans recouper les horodatages à la main.

## Contexte

Mesure du 2026-10-01 sur les 40 tickets approuvés du journal : 12 min
médianes jusqu'à l'approbation, puis **9 min médianes** entre l'approbation et
le ticket suivant. Ces 9 min sont invisibles : documentation, rebase, PR,
attente de CI et merge n'écrivent rien dans le journal. Seuls le codeur et le
reviewer y portent leur durée (`terminé (Xms)`) ; celles de la sécurité et du
validateur se déduisent d'un écart entre deux lignes.

Le motif d'un refus est en plus perdu : `orchestrator.py:319-321` journalise
`(reason or '')[:100]`, alors que la ligne 318 transmet au codeur
`reason or raw_verdict[:500]`. Cinq des quatorze lignes
`CHANGES_REQUESTED tour N:` du journal sont vides.

## Solution proposée

- `run_security_audit` et `run_validation` (`services/pipeline_stages.py`)
  mesurent leur durée et l'ajoutent à leur ligne de journal existante.
- `_documenter_le_run` journalise sa fin avec sa durée et le nombre de
  fichiers modifiés, ou son échec.
- Après la livraison, l'orchestrateur journalise une ligne par étape de
  `Livraison.etapes` avec sa durée, et `arret` s'il y en a un. `Livraison`
  gagne pour cela une durée par étape ; l'attente de CI est une étape à part.
- La ligne `CHANGES_REQUESTED` journalise le même texte que celui transmis au
  codeur, tronqué à 100 caractères.

## Critères d'acceptation

- [ ] Un test vérifie que la ligne de journal de l'audit sécurité contient sa
      durée en millisecondes
- [ ] Un test vérifie que la ligne de journal du validateur contient sa durée
      en millisecondes
- [ ] Un test vérifie qu'une documentation réussie écrit une ligne avec sa
      durée et son nombre de fichiers, et qu'un échec écrit une ligne d'échec
- [ ] Un test vérifie qu'une livraison écrit une ligne par étape, dont une
      pour l'attente de CI, chacune avec sa durée
- [ ] Un test vérifie qu'un reviewer sans motif structuré produit une ligne
      `CHANGES_REQUESTED` qui reprend le début de son verdict brut

## Ce que ça ne fait pas

Rien n'est accéléré : ce ticket mesure, pour que les tickets 291 et 292
s'appuient sur des chiffres et non sur une estimation.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

`Livraison` est sérialisé dans `LIVRAISON_DONE` (`data=livraison.__dict__`) :
le nouveau champ doit rester sérialisable en JSON.