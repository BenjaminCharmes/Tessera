---
id: ticket-093
title: "Le nom d'un projet n'est pas le nom d'un fichier"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-092]
estimated_days: 1
created: 2026-09-18
---

# ticket-093 — « Lyra — CLAUDE.md »

## Pourquoi

La barre latérale affichait :

```
Lyra — CLAUDE.md
FluentDB — CLAUDE.md
CLAUDE.md — projet ide-core
Orion Analytics — CLAUDE.md
```

Deux causes qui se rencontrent :

1. ADR-007 fait du **premier titre du CLAUDE.md** le nom du projet.
2. Le prompt `project-analyzer` demande d'écrire `# CLAUDE.md — NomDuProjet`.

Le titre servait deux choses à la fois : annoncer le fichier, et nommer le
projet. Les deux ne veulent pas la même chose. Un en-tête de fichier dit
« ceci est le CLAUDE.md de X » ; un nom de projet dit « X ».

## Critères d'acceptation

- [x] `# Lyra — CLAUDE.md` donne `Lyra`
- [x] `# CLAUDE.md — projet ide-core` donne `ide-core`
- [x] `# Orion Analytics` est laissé intact
- [x] `# CLAUDE.md` seul retombe sur le nom du dossier
- [x] Le prompt `project-analyzer` n'écrit plus la décoration
- [x] Les sept `CLAUDE.md` existants sont corrigés

## Note

Les projets pro sont des symlinks vers des dépôts clients. Leur `CLAUDE.md`
est exclu par `.git/info/exclude` (ADR-021, ADR-023) : `git status` y est resté
vide après la correction. C'est exactement ce que cette ADR existe pour
garantir, et c'était l'occasion de le vérifier en vrai.
