---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 1
id: ticket-432
plan: true
pr_number: null
priority: high
status: done
title: Tessera captures a project's screens at phone and desktop width, light and
  dark, to compare them with the mockup
type: feat
---

# ticket-432 — Capturer les écrans d'un projet

## Objectif

Produire en un geste les captures d'un projet lancé — téléphone 390 px et
ordinateur 1440 px, thèmes clair et sombre, pour chaque écran déclaré —
afin de les comparer à `design/maquette/` (ticket-419).

## Contexte

Demandé deux fois le 2026-10-14, par affût et par vigie (récupérés, voir
ticket-430), et refait à la main sur curio le 13/10 et sur Tessera le
14/10 : Playwright installé dans un dossier temporaire, chemin vers le
Chromium déjà présent, ouverture de session avec le jeton, un clic par
onglet, quatre captures par écran. Edge headless exige un profil par
capture et ne descend pas sous ~500 px.

Le frontend de Tessera a déjà `@playwright/test` et son navigateur pour ses
tests de bout en bout.

## Solution proposée

- `agents.json` d'un projet peut déclarer
  `"captures": { "url": "http://localhost:5196", "ecrans": [{ "nom":
  "accueil", "chemin": "/" }, { "nom": "quiz", "chemin": "/#jouer" }] }`
  (et, au besoin, une action de clic par écran : `"clic": "Jouer"`).
- Un script `scripts/captures.mjs` (Playwright du frontend de Tessera)
  prend un projet et produit `<nom>-<390|1440>-<clair|sombre>.png` en
  émulant `prefers-color-scheme`.
- `POST /api/v1/projects/{id}/captures` le lance, écrit les images dans un
  dossier hors du dépôt du projet (artefacts Tessera, ADR-021) et renvoie
  leur liste ; `GET /api/v1/projects/{id}/captures/{fichier}` les sert.
- 409 si le projet ne déclare pas `captures` ou si son app ne répond pas à
  `url`.

## Critères d'acceptation

- [ ] Un test vérifie la lecture de `captures` dans `agents.json`, et 409
      quand elle manque
- [ ] Un test (exécuteur simulé) vérifie que deux écrans donnent huit
      captures nommées `<nom>-<largeur>-<thème>.png`
- [ ] Un test vérifie que les images sont écrites hors du dépôt du projet
- [ ] Un test vérifie 409 quand l'app du projet ne répond pas
- [ ] `docs/guide-utilisateur.md` explique comment déclarer `captures`

## Dépendances

Aucune.

## Ce que ça ne fait pas

- Pas de comparaison automatique avec la maquette : les captures se
  regardent à côté d'elle (un usage par le validateur viendra ensuite).