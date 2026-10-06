---
agent: codeur
created: 2026-10-05
depends_on:
- ticket-343
estimated_days: 0.5
id: ticket-346
pr_number: null
priority: high
status: done
title: Git paths with accents are read unquoted, so their tickets are not swept into
  a run's commit
type: fix
---

# ticket-346 — Les chemins accentués sont lus sans guillemets

## Objectif

Un ticket dont le nom de fichier porte un accent est reconnu par
`GitWorkspace` sous son vrai chemin : il n'est ni balayé dans le commit d'un
autre run, ni oublié quand Tessera le déplace.

## Contexte

`_untracked_files` (`backend/src/tessera/services/git_workspace.py`) lit
`git ls-files --others --exclude-standard` ligne par ligne. Sans `-z` ni
`core.quotePath=false`, git rend un chemin non ASCII entre guillemets,
octets échappés : `"tickets/todo/ticket-004-clavier-fl\303\250ches.md"`. Ce
texte ne correspond à aucun chemin réel.

Le 2026-10-05, sur le projet `serpent` (8 tickets non suivis, posés par le
planificateur), le commit de suivi du ticket-001 (`0fca43d`) a embarqué les
cinq tickets à accent, présents avant le run : leur chemin quoté ne
correspondait pas au relevé de départ. Le ticket-002 est ensuite parti d'une
branche issue de `main`, sans ses fichiers : « Ticket introuvable :
ticket-002 », file interrompue.

Le ticket-343 réduit les dégâts (un fichier non suivi n'est commité que si
son nom de fichier figure parmi les tickets suivis), mais compare des noms de
fichier lus de la même façon : un ticket **suivi** à accent, déplacé de
`todo/` à `done/`, aurait son nouveau chemin quoté et ne serait pas reconnu
comme un déplacement. Le démineur a de tels tickets
(`ticket-021-spécification-visuelle-…`).

## Solution proposée

Toute lecture de chemins dans `GitWorkspace` (`ls-files`, `diff
--name-only`, `status --porcelain` s'il y en a) passe `-z` et découpe sur
`\0` — ou, à défaut, `-c core.quotePath=false`. Une seule fonction utilitaire
pour ça, réutilisée.

## Critères d'acceptation

- [ ] Un test crée, dans un dépôt temporaire, un fichier non suivi `tickets/todo/ticket-004-flèches.md` et vérifie que `_untracked_files` rend ce chemin exact, sans guillemets ni octets échappés
- [ ] Un test vérifie qu'un ticket non suivi à accent, présent avant le run, ne figure pas dans le commit de suivi
- [ ] Un test vérifie qu'un ticket suivi à accent, déplacé de `tickets/todo/` à `tickets/done/` pendant le run, figure dans le commit de suivi à son nouveau chemin
- [ ] Aucune lecture de liste de chemins dans `git_workspace.py` ne découpe plus une sortie git sur les retours à la ligne sans `-z` ou `core.quotePath=false`

## Ce que ça ne fait pas

- Ne renomme aucun ticket existant.
- Ne répare pas le dépôt `serpent` : ses tickets sont remis sur `main` à la main.

## Dépendances

ticket-343 (même code, PR #265).

## Risques

Un second commit de suivi (`56b8aa4`, même dépôt) a embarqué les tickets 002
et 003, sans accent. La cause n'est pas établie ; avec le ticket-343, un
fichier non suivi absent des tickets suivis n'est plus commité du tout, ce qui
devrait couvrir ce cas. À vérifier sur le prochain run d'un projet neuf.