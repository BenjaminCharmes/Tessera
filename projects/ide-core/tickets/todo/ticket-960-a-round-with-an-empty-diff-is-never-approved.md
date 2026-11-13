---
agent: codeur
created: 2026-11-13
depends_on: []
estimated_days: 0.5
id: ticket-960
pr_number: null
priority: high
status: todo
title: "A round whose diff is empty is never approved, whatever the verdicts say"
type: fix
---

# ticket-960 — Un tour dont le diff est vide n'est jamais approuvé

## Objectif

Qu'un run ne puisse pas être approuvé sur le récit du codeur quand il n'a
rien changé.

## Contexte

Run du ticket-958 (12/11, 18:38, run a9792a50) : la garde d'écriture a refusé
la première écriture du codeur (défaut corrigé par le ticket-959), qui s'est
arrêté sans rien écrire. Au tour 1, le validateur a rendu `APPROVED`,
`all_passed: true`. Seul le refus du reviewer a empêché l'approbation.

La cause est dans `_capture_diff` (`services/pipeline/pipeline_production.py`).
Quand `diff_depuis_base` est vide, elle renvoie la **prose du codeur**, que
l'audit, le reviewer et le validateur lisent comme `reviewed_code`. Un codeur
qui décrit un travail qu'il n'a pas fait peut donc passer les trois portes
sans une ligne de code.

## Solution proposée

1. `_capture_diff` dit si le diff réel était vide (un drapeau sur le run, par
   exemple `run.diff_vide`), en plus de ce qu'elle renvoie aujourd'hui.
2. Dans `_run_rounds` (`services/pipeline/orchestrator.py`), un tour dont le
   diff réel est vide n'est pas approuvé, même si reviewer et validateur
   approuvent. Le retour au codeur dit « aucun fichier modifié : rien à
   approuver ».
3. L'échec de calcul du diff (`GitWorkspaceError`) compte comme un diff vide :
   la porte échoue fermée (ADR-037).
4. Sans espace git (`_git_workspace is None`), rien ne change.

## Critères d'acceptation

- [ ] Un test : avec un diff réel vide et deux verdicts `APPROVED`, le tour
      n'est pas approuvé et le retour au codeur contient « aucun fichier
      modifié ».
- [ ] Un test : avec un diff non vide et deux verdicts `APPROVED`, le tour est
      approuvé, comme aujourd'hui.
- [ ] Un test : une `GitWorkspaceError` au calcul du diff empêche
      l'approbation du tour.
- [ ] Un test : sans espace git, un tour approuvé par les deux verdicts reste
      approuvé.

## Ce que ça ne fait pas

- Ne change pas ce que les portes reçoivent : la prose reste leur repli, elle
  ne suffit simplement plus à approuver.
- Ne traite pas un diff non vide mais hors sujet : c'est le rôle du reviewer
  et du validateur.
