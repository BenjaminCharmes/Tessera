---
id: ticket-196
title: "Régler le pipeline d'un projet depuis l'UI"
type: feat
status: done
pr_number: 62
priority: medium
agent: codeur
depends_on: []
estimated_days: 1.5
created: 2026-09-26
---

# ticket-196 — Régler le pipeline d'un projet depuis l'UI

## Objectif

Activer le testeur, la sécurité et le validateur, poser la commande de
test, choisir l'autonomie et `merge_without_ci`, sans ouvrir `agents.json`.

## Contexte

`AgentPipelineConfig` porte `testeur_enabled`, `test_command`,
`securite_enabled`, `validateur_enabled`, `max_review_rounds` ; le manifeste
porte aussi `autonomy` et `merge_without_ci`. Aucun n'est visible ni
modifiable dans le frontend : seul le modèle d'un agent l'est
(`projects.py:493`). Le `CLAUDE.md` d'`ide-core` explique sur un paragraphe
pourquoi son testeur est éteint — c'est le genre d'information qu'un écran
de réglage devrait porter.

## Solution proposée

- Backend : `GET /projects/{id}/pipeline` rend la configuration effective
  (défauts appliqués), et `PATCH /projects/{id}/pipeline` réécrit les seuls
  champs reçus dans `agents.json`, en préservant le reste du fichier comme
  le fait `set_agent_model`. `autonomy` et `merge_without_ci` en font
  partie.
- Validation : `testeur_enabled: true` sans `test_command` est refusé (400)
  — la raison est dans le docstring de `AgentPipelineConfig`. `autonomy`
  hors de `commit | pr | merge` est refusé.
- Frontend : un onglet « Pipeline » dans le panneau projets, avec pour
  chaque interrupteur une ligne qui dit ce qu'il coûte : « un appel LLM de
  plus par tour » pour sécurité et validateur, « lance `test_command` depuis
  le dossier du projet, sans shell » pour le testeur.
- `autonomy: merge` affiche l'avertissement d'ADR-029 et ADR-045 avant
  d'enregistrer : merger, c'est décider qu'un travail est bon.
- Un projet en cours de run ne se modifie pas : la politique est lue une
  fois avant le premier agent (ADR-027), un changement ne s'appliquerait
  qu'au run suivant, et l'écran doit le dire.

## Critères d'acceptation

- [ ] Un test backend vérifie que le PATCH préserve `services`, `artifacts`
      et `git_root` du manifeste
- [ ] Un test vérifie le refus de `testeur_enabled` sans `test_command`
- [ ] Un test vérifie le refus d'une `autonomy` inconnue
- [ ] Un test frontend vérifie que l'avertissement s'affiche avant
      d'enregistrer `merge`
- [ ] Un test frontend vérifie que l'onglet est en lecture seule pendant un
      run du projet
- [ ] `test_consignes_coherentes.py` passe : chaque champ de
      `AgentPipelineConfig` reste lu quelque part
- [ ] `uv run pytest`, `uv run mypy src/`, `npm run test`, `npm run build`
      passent

## Ce que ça ne fait pas

Pas d'édition des services (`services`) ni du dépôt distant. Pas de
réglage du provider par rôle : c'est le ticket-188.

## Dépendances

Aucune.

## Estimation

1,5 jour.

## Risques

Le manifeste est aussi ce que les agents n'ont pas le droit d'écrire
(ADR-027, `chemins_proteges`). Le PATCH est une action de l'utilisateur, pas
d'un agent : il passe par le backend, jamais par un outil d'agent.
