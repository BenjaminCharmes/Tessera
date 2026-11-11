---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 1
id: ticket-936
plan: true
pr_number: null
priority: high
status: blocked
title: A hosted project's description is never replaced with Tessera's own
type: fix
---

# ticket-936 — La description d'un projet hébergé ne prend jamais celle de Tessera

## Objectif

Que la documentation d'un run n'écrive dans `agents.json` qu'une description
du projet lui-même.

## Contexte

Le 11/11, pendant le run du ticket-018 de homelab-monitor, la documentation a
remplacé la description du projet par
« Tessera est un IDE multi-projets avec orchestration d'agents IA,
auto-hébergé. Le tableau de bord, servi par le backend, fonctionne depuis
n'importe quelle machine du réseau. » La première phrase est celle du
`CLAUDE.md` racine de Tessera. La vue Projets et l'Historique ont affiché
cette description pour Homelab Monitor jusqu'à sa correction à la main
(homelab-monitor PR #32).

Deux trous :

- le service de documentation (`services/documentation/`) a eu sous les yeux
  le `CLAUDE.md` de Tessera pour un projet hébergé, alors que le ticket-414
  tient les consignes ancêtres à l'écart des agents d'un projet hébergé ;
- `ecrire_description` (`services/documentation/documentation_description.py`)
  contrôle la forme et la preuve (ADR-057), pas le sujet : une phrase prise
  ailleurs passe si ses jetons figurent dans la matière lue.

## Solution proposée

- Le plan trouve par quel chemin le contenu du `CLAUDE.md` de Tessera atteint
  doc-technique sur un projet hébergé (contexte du prompt, fichiers fournis,
  consignes du SDK) et le ferme.
- `ecrire_description` refuse une proposition qui reprend la première phrase
  de la description d'un **autre** projet (celles des `agents.json` voisins)
  ou du `CLAUDE.md` racine de Tessera, hors du projet ide-core.

## Critères d'acceptation

- [ ] Un test de `backend/tests/` vérifie que, pour un projet hébergé, une
      proposition qui commence par la première phrase du `CLAUDE.md` racine
      de Tessera est refusée avec un motif qui le dit.
- [ ] Un test vérifie qu'une proposition qui reprend la description d'un
      autre projet est refusée.
- [ ] Un test vérifie qu'une description propre au projet, qui cite Tessera
      en passant (« Sert à mesurer l'orchestration de Tessera »), est
      acceptée.
- [ ] Un test vérifie, avec des doubles, que la matière fournie à
      doc-technique pour un projet hébergé ne contient pas le `CLAUDE.md`
      racine de Tessera.

## Ce que ça ne fait pas

- Ne juge pas la qualité d'une description, seulement qu'elle n'est pas
  celle d'un autre.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Le chemin de fuite peut être le prompt système du rôle lui-même : le plan le
dit avant de toucher au code.