---
agent: codeur
created: 2026-11-10
depends_on: []
estimated_days: 1
id: ticket-913
pr_number: 1030
priority: medium
status: done
title: A monthly housekeeping report points at what grew or went stale
type: feat
---

# ticket-913 — Un relevé de ménage montre ce qui a grossi ou vieilli

## Objectif

Donner au ménage mensuel une mesure, sans LLM : quels fichiers de mémoire
grossissent, quelles décisions ne servent plus, quels tickets dorment.

## Contexte

`contraintes.md`, `decisions.md` d'ide-core, `lecons.md` et les `CLAUDE.md`
ont leur budget ou leur archive, testés. Le reste grossit sans que personne
ne regarde : les `memory/` des autres projets, leurs `decisions.md`, les
journaux, les tickets en `blocked/`. Un ménage sans mesure se fait au jugé,
ou pas du tout.

## Solution proposée

- Un module `services/projets/releve_menage.py` et un script
  `scripts/releve_menage.py [--projets a,b] [--age-jours 30]`.
- Pour chaque projet de `projects/` qui porte un `CLAUDE.md` :
  - chaque fichier de `memory/` avec sa taille en caractères et en lignes,
    du plus gros au plus petit ;
  - le nombre d'ADR de `memory/decisions.md` (titres `## ADR-`), et celles
    qu'aucun autre fichier du projet ne cite par leur numéro ;
  - le nombre de lignes de `memory/pipeline-log.md` et la date de sa plus
    vieille ligne ;
  - les tickets de `tickets/blocked/` dont le dernier commit git date de
    plus de `--age-jours`, avec cette date.
- Sortie Markdown sur la sortie standard, un titre par projet.

## Critères d'acceptation

- [ ] `backend/src/tessera/services/projets/releve_menage.py` expose une
      fonction publique qui prend une racine de projets et un âge en jours,
      et rend le Markdown.
- [ ] Un test vérifie que les fichiers de `memory/` sont listés du plus gros
      au plus petit, avec leur taille en caractères.
- [ ] Un test vérifie qu'une ADR citée dans un autre fichier du projet n'est
      pas signalée, et qu'une ADR citée nulle part l'est.
- [ ] Un test vérifie que la date de la plus vieille ligne du journal est
      rendue.
- [ ] Un test vérifie qu'un ticket bloqué plus récent que `age_jours` n'est
      pas signalé, et qu'un plus ancien l'est.
- [ ] `scripts/releve_menage.py` accepte `--projets` et `--age-jours`, et un
      test l'exécute sur un dossier temporaire.

## Ce que ça ne fait pas

- N'écrit, n'archive ni ne supprime rien : il mesure. Le tri se propose
  ensuite dans une PR (ticket-911).
- Ne lit pas la mémoire des sessions Claude, hors du dépôt.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Une ADR citée seulement par une autre ADR périmée paraît vivante : le relevé
signale, l'humain tranche.