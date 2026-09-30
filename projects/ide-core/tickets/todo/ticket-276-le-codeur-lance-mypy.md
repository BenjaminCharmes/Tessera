---
id: ticket-276
title: "The codeur's self-check runs mypy after touching Python"
type: chore
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-30
---

# ticket-276 — Le codeur lance mypy quand il touche du Python

## Objectif

Qu'une erreur de typage Python revienne au codeur pendant son tour, et plus à
la CI après la PR.

## Contexte

Deux fois le 2026-09-30, une PR approuvée par reviewer et validateur a eu une CI
rouge sur le seul `mypy src/` :
- PR #136 (ticket-268) : `Missing type arguments for generic type "dict"` ;
- PR #140 (ticket-275) : `Unused "type: ignore" comment` puis
  `"object" has no attribute "__iter__"`.

Les deux ont été corrigées à la main. Le skill du codeur,
`projects/ide-core/.claude/skills/verifier-mon-travail/SKILL.md`, fait lancer
les fichiers de test touchés et `tsc -b` pour le TypeScript — mais rien pour le
typage Python, alors que la CI lance `uv run mypy src/` (le job Backend).

## Solution proposée

- Dans la section « Ce que tu lances » du skill, ajouter pour le backend :
  « et le typage si tu as touché du Python :
  `cd ../../backend && uv run mypy src/` ». La commande dure une dizaine de
  secondes sur tout `src/` : pas de ciblage par fichier, qui manquerait les
  erreurs d'import croisé.
- Même traitement de la sortie que les tests : erreur → corriger et relancer,
  trois essais au plus ; succès → recopier la ligne réelle
  (`Success: no issues found in N source files`) dans « Vérification ».

## Critères d'acceptation

- [ ] `projects/ide-core/.claude/skills/verifier-mon-travail/SKILL.md` contient
      la commande `uv run mypy src/`.
- [ ] Le skill dit de recopier la ligne de résultat de mypy dans la section
      « Vérification » du rapport.
- [ ] Le diff ne modifie que ce fichier de skill.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Consigne uniquement.

## Risques

Aucun : une commande de plus par tour qui touche du Python.
