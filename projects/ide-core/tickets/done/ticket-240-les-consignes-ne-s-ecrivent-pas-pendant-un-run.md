---
id: ticket-240
title: "Un agent n'écrit ni CLAUDE.md ni les skills pendant un run"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-240 — Un agent n'écrit ni CLAUDE.md ni les skills pendant un run

## Objectif

Refuser à un agent l'écriture des fichiers de consignes que le CLI charge dans
chaque session : `CLAUDE.md`, `CLAUDE.local.md`, et `.claude/skills/`,
`.claude/commands/`, `.claude/agents/`.

## Contexte

`chemins_proteges.py` (ticket-119) protège ce qui borne le run : `agents.json`,
`.git/`, `.claude/settings*.json`, `.github/workflows/`. Il laisse ouverts les
fichiers qui disent à **tous les agents suivants** comment se comporter. Un
codeur peut réécrire `CLAUDE.md` en silence ; le changement part dans chaque
session du CLI, et la règle 5 de `CLAUDE.md` (aucune modification sans ticket)
n'y est tenue par rien.

Même raisonnement que pour `.claude/settings*.json` : ce sont des instructions
que le run suivant exécute, pas du code du projet.

## Solution proposée

Étendre `motif_de_protection` : tout fichier nommé `CLAUDE.md` ou
`CLAUDE.local.md`, où qu'il soit sous la racine, et tout chemin sous
`.claude/skills/`, `.claude/commands/` ou `.claude/agents/`. Le motif dit
pourquoi, comme les autres.

Les autres fichiers de `.claude/` restent écrivables (`frontend/.claude/notes.md`
passe déjà et doit continuer de passer).

## Critères d'acceptation

- [ ] `test_chemins_proteges.py` vérifie qu'un `Write` sur `CLAUDE.md`, `sous/dossier/CLAUDE.md`, `CLAUDE.local.md`, `.claude/skills/x/SKILL.md`, `.claude/commands/x.md` et `.claude/agents/x.md` est refusé
- [ ] `test_chemins_proteges.py` vérifie que `docs/CLAUDE-notes.md` et `frontend/.claude/notes.md` passent
- [ ] Le motif de refus pour `CLAUDE.md` nomme le fichier et dit qu'il est chargé dans chaque session

## Ce que ça ne fait pas

- Un ticket qui demande explicitement de modifier `CLAUDE.md` ne passe plus par
  le codeur : la modification se décrit dans le rapport, ou passe par le lot de
  documentation (ticket-244), qui écrit sans les outils de l'agent.
- `python -c` contourne toujours le contrôle sur `Bash` (ADR-031).
