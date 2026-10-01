---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 1
id: ticket-282
pr_number: null
priority: medium
status: blocked
title: Agent cards share one verdict header, icons stay on their text's line, tooltips
  are not clipped
type: fix
---

# ticket-282 — Les cartes d'agents parlent la même langue

## Objectif

Que les quatre cartes de la vue du run affichent leur verdict de la même
façon, que leur résumé replié se comprenne, et que les icônes et bulles d'aide
restent lisibles.

## Contexte

Retour d'usage du 2026-10-01 :

- `components/FilDuRun/index.tsx` a trois en-têtes écrits séparément.
  Sécurité et validateur affichent `IconCheck`/`IconCross` devant leur
  verdict ; `EntreePipeline` (codeur, reviewer) n'en affiche aucun : on lit
  « ✓ PASS », « ✓ APPROVED » et « APPROVED » sans icône.
- Replié, le codeur affiche `resumePassage()` : la première ligne de son
  rapport, tronquée à `max-w-48` — un fragment comme « `python-multipart` est
  absent des… » qui ne dit pas ce qu'est la carte.
- Tailwind v4 rend les `svg` en `display: block` : une icône dans un conteneur
  non flex prend sa ligne. `VerdictBanner` l'a corrigé (ticket-227) ; restent
  `AgentPanel/PipelineSummary.tsx:34-44`,
  `Sidebar/CreateProjectModal.tsx:84-85`,
  `Sidebar/ImportProjectModal.tsx:335-336` et `Sidebar/ProjectNav.tsx:83-87`.
- `design/InfoTip.tsx` place sa bulle en `absolute` dans la sidebar, qui est
  `overflow-hidden` (`App.tsx:44`) : la bulle est coupée au bord de la
  sidebar, et `z-50` n'y peut rien.

## Solution proposée

- Un seul composant d'en-tête de verdict, utilisé par les quatre cartes :
  icône d'état, mot du verdict, chevron si la carte se replie. Le reviewer y
  passe `APPROVED` / `CHANGES_REQUESTED` avec son icône.
- Le résumé replié du codeur dit ce qu'est la carte en termes stables —
  « terminé · 2 min 50 », depuis le `duration_ms` d'`agent_done` — et son
  rapport reste lisible une fois déplié.
- Les quatre conteneurs cités passent en `inline-flex items-center gap-1`.
- `InfoTip` rend sa bulle dans un portal sur `document.body`, positionnée en
  `fixed` à partir du rectangle de l'icône.

## Critères d'acceptation

- [ ] Un test de `FilDuRun` vérifie qu'une entrée reviewer approuvée, une
      entrée sécurité `PASS` et une entrée validateur `APPROVED` rendent toutes
      les trois la même icône de succès dans leur en-tête
- [ ] Un test vérifie que l'en-tête replié du codeur affiche sa durée et ne
      contient pas la première ligne de son rapport
- [ ] Un test vérifie que l'icône et le titre de `PipelineSummary` sont dans
      un même conteneur `flex` ou `inline-flex`
- [ ] `CreateProjectModal`, `ImportProjectModal` et `ProjectNav` placent leur
      icône dans un conteneur `flex` ou `inline-flex`
- [ ] Un test d'`InfoTip` vérifie que la bulle est rendue sous `document.body`
      et non dans le parent de l'icône
- [ ] Le test de palette d'ADR-026 passe sans exception ajoutée

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

ADR-026 : le violet ne s'emploie pas en couleur de texte ; l'en-tête commun
reprend les couleurs d'état existantes.