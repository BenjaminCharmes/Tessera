---
id: ticket-039
title: "Packaging desktop — build Tauri utilisable au quotidien"
type: chore
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-07-11
---

# ticket-039 — Packaging desktop pour un usage quotidien

## Objectif

Permettre de lancer vibe-ide comme une vraie application desktop (double-clic,
une seule fenêtre), sans avoir à démarrer manuellement deux serveurs de dev
(`make dev` + `make dev-frontend`) à chaque utilisation.

## Contexte

`make tauri-build` existe déjà et produit un bundle de production via Tauri,
mais le backend FastAPI n'est pas packagé avec — il faut toujours le lancer
séparément. Le mode dev actuel (2 terminaux) est adapté à l'itération sur le
code, pas à un usage "utilisateur final" au jour le jour.

## Solution proposée

À déterminer précisément au moment de l'implémentation, mais l'idée générale :

- Faire en sorte que le bundle Tauri packagé lance/gère aussi le processus
  backend (ex. sidecar process Tauri, ou binaire backend embarqué), pour
  n'avoir qu'un seul exécutable à lancer.
- Documenter dans le `README.md` la procédure de build + lancement de l'app
  packagée (`make tauri-build` puis où trouver/lancer l'exécutable généré).
- Optionnel : un raccourci `make run` pour le mode dev qui lance backend +
  frontend en parallèle dans un seul terminal, pour les sessions de test rapide
  qui ne nécessitent pas le vrai packaging.

## Critères d'acceptation

- [ ] Un utilisateur peut lancer l'app packagée (build Tauri) sans avoir à
      démarrer manuellement le backend dans un terminal séparé
- [ ] Le README documente clairement la procédure de build + lancement
- [ ] `make tauri-dev` et le mode dev classique restent fonctionnels sans
      changement pour les développeurs

## Dépendances

Aucune.

## Estimation

**1j** — Investigation de l'approche sidecar Tauri + intégration + doc.

## Risques

- **Moyen** — Empaqueter un backend Python dans un bundle Tauri (Rust) n'est
  pas trivial (taille du bundle, gestion du cycle de vie du process, chemins
  relatifs à l'exécutable packagé plutôt qu'au repo). À valider avant de
  s'engager sur l'estimation.
