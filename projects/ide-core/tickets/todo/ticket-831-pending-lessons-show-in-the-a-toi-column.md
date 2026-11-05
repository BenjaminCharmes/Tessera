---
id: ticket-831
title: "Lessons waiting for approval show in the « À toi » column"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-801", "ticket-803"]
estimated_days: 1
created: 2026-11-05
---

# ticket-831 — Les leçons qui attendent une validation apparaissent dans « À toi »

## Objectif

Benjamin voit qu'une leçon attend sa validation sans aller ouvrir `memory/lecons.md`.

## Contexte

ADR-074 : le service propose une leçon sous `## Proposées` de `memory/lecons.md` (ticket-803) ;
seul un humain la déplace sous `## En vigueur`. Benjamin, le 05/11 : « si ça demande une
relecture de ma part, ça risque de bloquer si je ne vois pas qu'un agent a écrit dedans ». Rien
ne bloque (une leçon proposée n'a aucun effet), mais une leçon jamais vue n'apporte rien. La
colonne « À toi » du Bureau (`frontend/src/lib/bureau/aToi.ts`, `ColonneAToi.tsx`) liste déjà
ce qui attend Benjamin (questions, PR à relire).

## Solution proposée

- Backend : la réponse qui décrit un projet à la colonne « À toi » (la route déjà lue par
  `ColonneAToi`, à identifier) porte `lecons_proposees: int`, compté par le module
  `backend/src/tessera/services/lecons.py` du ticket-801 ; 0 quand le fichier est absent ou
  illisible, jamais une erreur.
- Frontend : `contenuAToi` ajoute, par projet qui en a, une ligne « N leçon(s) à valider » qui
  nomme `memory/lecons.md` ; aucune ligne à 0.

## Critères d'acceptation

- [ ] Un test backend vérifie que `lecons_proposees` vaut le nombre de lignes sous `## Proposées`
      d'un `memory/lecons.md` temporaire, et 0 sans fichier
- [ ] Un test de `frontend/src/lib/bureau/aToi.test.ts` vérifie la ligne « 2 leçons à valider »
      pour un projet qui en a deux, et aucune ligne pour un projet à 0
- [ ] Un test de `ColonneAToi.test.tsx` vérifie que la ligne s'affiche avec le nom du projet

## Ce que ça ne fait pas

Aucune validation depuis l'interface : la leçon se déplace toujours à la main dans le fichier
(ADR-074, ADR-055).
