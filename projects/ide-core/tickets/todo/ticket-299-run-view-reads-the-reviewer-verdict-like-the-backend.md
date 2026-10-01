---
id: ticket-299
title: "The run view reads the reviewer's verdict from its opening line, like the backend"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-01
---

# ticket-299 — La vue du run lit le verdict du reviewer comme le backend

## Objectif

Qu'une approbation du reviewer qui cite `CHANGES_REQUESTED` dans son corps
s'affiche « APPROVED » dans la vue du run.

## Contexte

Le ticket-298 a corrigé le backend : le verdict est la première ligne qui
**commence** par `APPROVED` ou `CHANGES_REQUESTED`, une fois retirée la mise
en forme Markdown. La règle d'avant (`CHANGES_REQUESTED` n'importe où
l'emporte) ne joue plus qu'en l'absence d'une telle ligne.

Le frontend applique encore l'ancienne règle :
`components/FilDuRun/index.tsx:114-115` fait
`content.includes("APPROVED") && !content.includes("CHANGES_REQUESTED")`.
L'écran affiche donc « CHANGES_REQUESTED » sur une revue que le pipeline a
approuvée. C'est arrivé trois fois sur le ticket-288.

## Solution proposée

- Une fonction `verdictDuReviewer(content)`, dans un petit module à part,
  qui applique la règle de `services/pipeline_text._parse_reviewer_verdict` :
  la première ligne de verdict l'emporte, puis l'ancienne règle, et une
  réponse sans verdict refuse.
- `FilDuRun` l'utilise à la place du `includes`.

## Critères d'acceptation

- [ ] Un test vérifie que `verdictDuReviewer` rend « APPROVED » pour
      `"APPROVED\n\n- Bug \`CHANGES_REQUESTED\` corrigé"`
- [ ] Un test vérifie qu'un `**APPROVED**` précédé d'une ligne de prose rend
      « APPROVED »
- [ ] Un test vérifie qu'un `## CHANGES_REQUESTED: motif` en tête rend
      « CHANGES_REQUESTED »
- [ ] Un test vérifie qu'une réponse sans verdict rend « CHANGES_REQUESTED »
- [ ] `FilDuRun/index.tsx` ne contient plus `includes("CHANGES_REQUESTED")`

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Deux implémentations d'une même règle finissent par diverger (ADR-034). Les
tests reprennent donc les mêmes cas que ceux du ticket-298.
