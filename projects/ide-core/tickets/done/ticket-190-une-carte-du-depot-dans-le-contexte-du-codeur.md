---
id: ticket-190
title: "Une carte du dépôt dans le contexte du codeur"
type: feat
status: done
pr_number: 54
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-26
---

# ticket-190 — Une carte du dépôt dans le contexte du codeur

## Objectif

Que le codeur sache où sont les fichiers avant son premier appel d'outil, au
lieu de le découvrir à coups de `Glob`.

## Contexte

Sur un run type, le codeur fait 13 `Glob` et une cinquantaine de `Read` avant
sa première écriture, et parmi ces lectures reviennent toujours les mêmes
fichiers de configuration : `CLAUDE.md`, `package.json`, `tsconfig.json`,
`vite.config.ts`. Chacun de ces tours renvoie tout l'historique : le coût est
multiplié par le nombre de tours, pas ajouté.

`_build_project_context` (`routers/orchestrator.py:86`) n'injecte aucune
liste de fichiers. Le ticket-187 évite la redécouverte au tour 2 ; celui-ci
évite la découverte au tour 1.

## Solution proposée

- Un service `CarteDuDepot` rend, sans LLM, l'arborescence des fichiers
  **suivis** du projet (`git ls-files`, donc `.gitignore` respecté, et
  `node_modules` absent), depuis la racine d'écriture du run — le dépôt
  ancêtre en `git_root: ancestor`, sinon le dossier du projet.
- Bornée : au-delà de 400 entrées, les dossiers les plus peuplés sont repliés
  en `dossier/ (n fichiers)`. Le résultat tient sous 6 000 caractères.
- Injectée dans le prompt utilisateur du codeur et de l'architect, sous
  `## Fichiers du projet`, avec une ligne d'instruction : « lis ce dont tu
  as besoin, ne relis pas cette carte ». Le reviewer ne la reçoit pas : il
  part du diff.
- Calculée une fois par run, avant le premier agent : le codeur ne doit pas
  voir une carte qui inclut déjà ses propres fichiers du tour précédent.

## Critères d'acceptation

- [ ] Un test vérifie que la carte ne contient que des fichiers suivis par
      git (un fichier ignoré n'y figure pas)
- [ ] Un test vérifie le repliement au-delà de 400 entrées et la borne de
      6 000 caractères
- [ ] Un test vérifie qu'en `git_root: ancestor` la carte part de la racine
      du dépôt
- [ ] Un test de `pipeline_stages` vérifie que le prompt du codeur contient
      `## Fichiers du projet` et que celui du reviewer ne le contient pas
- [ ] Un test vérifie qu'un projet qui n'est pas un dépôt git donne une
      carte vide sans lever
- [ ] `uv run mypy src/` passe

## Ce que ça ne fait pas

Pas de résumé du contenu des fichiers, pas de cache entre runs, pas de
sélection intelligente selon le ticket. La mesure de l'effet — nombre de
`Glob` par run dans `agent_events` avant et après — se fait à la main sur
la base, pas dans ce ticket.

## Dépendances

Aucune ; se combine avec ticket-187.

## Estimation

1 jour.

## Risques

Sur un dépôt de plusieurs milliers de fichiers, une carte repliée peut ne
plus dire grand-chose : le plafond est là pour que le coût reste borné, pas
pour garantir l'utilité sur tous les dépôts.
