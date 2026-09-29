---
id: ticket-246
title: "Le CLAUDE.md racine tient dans un budget, et ne décrit plus JSON-RPC"
type: docs
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-242"]
estimated_days: 1
created: 2026-09-29
---

# ticket-246 — Le CLAUDE.md racine tient dans un budget

## Objectif

**Ce ticket modifie `CLAUDE.md` à la racine** (règle 5) : le ramener sous
7 000 caractères, et mesurer ce budget comme celui des ADR.

## Contexte

Chaque session charge le `CLAUDE.md` racine (9 262 caractères), celui
d'ide-core (3 829) et `decisions.md` (39 623). Un CLAUDE.md n'est pas une
configuration imposée : chaque ligne concurrence les autres pour l'attention du
modèle, et plus le fichier s'allonge, moins une règle donnée est suivie.

Le fichier répétait deux fois le flux git (« Git » puis « Le flux de travail
courant »), justifiait trois fois l'import des ADR, et annonçait **JSON-RPC 2.0**
entre l'UI et l'orchestrateur, qu'aucun code n'utilise : depuis ADR-041, on
lance en HTTP et on observe sur une WebSocket. Une consigne fausse, chargée
dans chaque session.

## Solution proposée

- Réécrire `CLAUDE.md` à contenu utile égal : doublons retirés, stack corrigée,
  une ligne sur ce que voient les agents du produit (ticket-242).
- `test_consignes_coherentes.py` : `CLAUDE.md` ≤ 7 000 caractères,
  `projects/ide-core/CLAUDE.md` ≤ 6 000 (le budget du ticket-244).

## Critères d'acceptation

- [ ] `CLAUDE.md` fait moins de 7 000 caractères
- [ ] `CLAUDE.md` ne mentionne plus JSON-RPC
- [ ] `test_consignes_coherentes.py` contient `test_les_claude_md_tiennent_leur_budget` pour les deux fichiers
- [ ] Les tests existants sur le flux git, les skills annoncés et l'arborescence de `.claude/` passent sur le nouveau texte

## Ce que ça ne fait pas

- `decisions.md` reste importé en entier : c'est le poste le plus lourd, mais
  son import est un choix documenté, qui se rediscute à part.
