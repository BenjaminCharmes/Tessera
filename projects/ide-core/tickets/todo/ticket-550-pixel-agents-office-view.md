---
id: ticket-550
title: "Design of an animated office view where each running agent is a character"
type: design
status: todo
pr_number: null
priority: low
agent: architect
depends_on: ["ticket-549"]
estimated_days: 1
created: 2026-10-23
plan: true
---

# ticket-550 — Conception d'une vue « bureau » des agents

## Objectif
Décider si et comment Tessera montre ses agents en cours comme des
personnages animés, à la manière de l'extension VS Code Pixel Agents, pour
voir d'un coup d'œil, sur tous les projets, qui travaille, qui attend une
réponse et qui semble figé.

## Contexte
Benjamin a proposé l'idée le 23/10. Tessera a déjà les données : les runs
vivants (`RunRegistry`), leurs événements (`WS /orchestrator/observe`), le
rôle actif de chaque étape, les questions en attente (ADR-025) et, après le
ticket-549, la santé de chaque agent. L'intérêt n'est pas décoratif : la
vue doit faire ressortir ce qui demande une action humaine.

## À trancher par la conception
- Ce que montre un personnage : projet, rôle, état (ticket-549), question
  en attente, ticket en cours ; ce qu'un clic ouvre.
- Où vit la vue : variante de `SupervisionView` ou vue à part.
- Rendu : sprites dessinés pour Tessera (pas ceux de l'extension), canvas ou
  DOM, coût dans Tauri quand dix agents tournent, mouvement réduit
  (`prefers-reduced-motion`).
- Couleurs : charte de l'ADR-026 (états) et `violet` réservé à l'identité.
- Maquette Artifact Design avant tout ticket d'implémentation.

## Critères d'acceptation
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit la vue retenue, ou pourquoi elle est écartée
- [ ] Le livrable cite la maquette (lien ou fichier sous `design/maquette/`)
- [ ] Le livrable liste les tickets d'implémentation qui en découlent, chacun avec ses critères vérifiables

## Ce que ça ne fait pas
- N'implémente rien : ticket de conception.
