---
id: ticket-096
title: "Un projet non-code, et la protection qui suit"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-095]
estimated_days: 1
created: 2026-09-18
---

# ticket-096 — Le premier projet qui n'est pas du code

## Pourquoi

Un projet de gestion de carrière : lire un contrat, une convention collective
et des bulletins de paie, pour préparer des entretiens et des négociations.
Aucun code produit — le premier projet de ce type dans vibe-ide.

Il sert deux choses : l'usage réel, et l'épreuve du modèle de vibe-ide sur
autre chose qu'un dépôt de code.

## Ce que ça a révélé

`test_tout_prompt_livre_est_declare_natif` est tombé dès l'ajout du prompt
`analyste-carriere`. Le verrou disait « tout prompt livré est protégé »,
ticket-094 disait « est protégé ce que le code charge par son nom ». Un agent
déclaré par un **projet** du dépôt n'entrait dans aucune des deux formulations,
et restait supprimable d'un clic — son projet cessant alors de tourner.

La règle est donc : **qu'est-ce qui casse s'il disparaît ?** Deux motifs, un
seul suffit — le code le charge par son nom, ou un projet du dépôt le déclare.

## Critères d'acceptation

- [x] Un test dérive les agents déclarés par les `agents.json` des projets et
      exige qu'ils soient protégés
- [x] Le badge et son infobulle disent les deux motifs
- [x] Le projet est la racine de son propre dépôt git (ADR-024)
- [x] `sources/` est exclu ; vérifié en déposant un faux bulletin
- [x] La convention collective, document public, est la seule exception
- [x] `autonomy: commit` — rien ne part sur un distant tout seul
- [x] Le périmètre d'écriture confine les agents au projet : vérifié qu'ils ne
      peuvent pas écrire dans `backend/`
- [x] Le prompt interdit tout chiffre nominatif dans ce qui est synchronisé

## Ce que ça ne fait pas

Le pipeline reste `codeur → reviewer`, conçu pour du code. Ici l'analyste tient
le rôle du codeur et écrit du Markdown : mécaniquement ça marche, mais les
étapes testeur, sécurité et validateur n'ont aucun sens sur ce projet et
restent désactivées. Si l'usage confirme l'intérêt, un pipeline par type de
projet serait le vrai sujet.
