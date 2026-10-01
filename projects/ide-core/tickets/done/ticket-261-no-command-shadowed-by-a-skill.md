---
id: ticket-261
title: "No slash command shares a skill's name, and ship becomes a user-only skill"
type: chore
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-30
---

# ticket-261 — Aucune command ne porte le nom d'un skill

## Objectif

Que chaque slash command tapée dans ce dépôt exécute le fichier qui la décrit,
et que `ship` ne puisse se déclencher que sur demande explicite.

## Contexte

Quand une command de `.claude/commands/` et un skill de `.claude/skills/`
portent le même nom, Claude Code sert le **skill**. C'est le cas de
`new-ticket` et `run-tessera` : `.claude/commands/new-ticket.md` et
`.claude/commands/run-tessera.md` ne sont jamais lus. La liste des skills d'une
session le montre : `/new-ticket` et `/run-tessera` y portent la description du
skill, seul `/ship` celle de sa command.

Le dommage est faible, puisque ces deux commands ne font que renvoyer au skill,
mais `CLAUDE.md` les présente comme trois slash commands, ce qui est faux pour
deux d'entre elles. Et rien n'empêche une prochaine collision.

`ship` pousse et ouvre une PR. Aujourd'hui, seul le fait d'être une command
l'empêche de se déclencher parce que sa description correspond à la tâche. Un
skill avec `disable-model-invocation: true` garantit la même chose de façon
explicite, et se tape toujours en `/ship`.

## Solution proposée

1. Supprimer `.claude/commands/new-ticket.md` et `.claude/commands/run-tessera.md`.
2. Déplacer le contenu de `.claude/commands/ship.md` dans
   `.claude/skills/ship/SKILL.md`, avec `name: ship`, sa `description` actuelle
   et `disable-model-invocation: true`, puis supprimer la command et le
   dossier `.claude/commands/` s'il est vide.
3. **Ce ticket autorise la modification de `CLAUDE.md` (règle 5)** : remplacer la
   ligne `commands/<nom>.md` de l'arborescence `.claude/` et la phrase « Slash
   commands : … » par une description juste : tout skill se tape en `/nom`,
   `ship` ne se tape que comme ça. Ajouter `ship` à la liste « Skills
   disponibles ».
4. Dans `backend/tests/test_consignes_coherentes.py`, ajouter un test qui échoue
   si un fichier `.claude/commands/<nom>.md` a le même nom qu'un dossier
   `.claude/skills/<nom>/`.

## Critères d'acceptation

- [ ] `.claude/commands/new-ticket.md` et `.claude/commands/run-tessera.md` n'existent plus
- [ ] `.claude/skills/ship/SKILL.md` existe, son frontmatter porte `name: ship` et `disable-model-invocation: true`
- [ ] `.claude/commands/ship.md` n'existe plus
- [ ] `CLAUDE.md` ne mentionne plus `commands/<nom>.md` et cite `ship` dans la liste « Skills disponibles »
- [ ] `test_consignes_coherentes.py` contient un test qui échoue quand une command et un skill partagent un nom

## Dépendances

Aucune.

## Estimation

Une demi-journée au plus, surtout de la relecture.

## Risques

- La liste « Skills disponibles » de `CLAUDE.md` est peut-être confrontée au
  contenu de `.claude/skills/` par un test existant : l'ajout de `ship` doit la
  garder cohérente.
- Un skill ajouté en session n'apparaît qu'à la session suivante : vérifier
  `/ship` dans une session neuve, pas dans celle qui a fait le changement.
