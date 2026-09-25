---
id: ticket-167
title: "`.env.example` dit que GITHUB_TOKEN ne sert qu'à github-sync"
type: docs
status: done
pr_number: 16
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-167 — `.env.example` décrit un besoin périmé

## Objectif

Qu'un lecteur du fichier d'exemple sache quand `GITHUB_TOKEN` est nécessaire.

## Contexte

```
# [OPTIONNEL] GitHub sync — requis uniquement pour l'agent github-sync
# GITHUB_TOKEN=ghp_...
# GITHUB_REPO=owner/repo
```

C'était vrai avant ADR-029 et ADR-030. Depuis, **toute livraison** en
`autonomy: pr` ou `merge` en dépend : sans token, `LivraisonService` s'arrête
sur « GitHub n'est pas configuré pour ce projet ».

Constaté à l'usage : un projet en `autonomy: pr` a produit trois runs approuvés
dont aucun n'a ouvert sa PR, et le fichier censé expliquer la configuration
disait que le réglage manquant était optionnel et réservé à autre chose.

`GITHUB_REPO`, lui, reste bien propre à `github-sync` — la livraison lit le
dépôt par projet, dans `github_remote`.

C'est la dérive qu'ADR-034 vise : une consigne qui décrit un état antérieur du
produit, et que rien ne relit.

## Solution proposée

Distinguer les deux variables et dire, pour chacune, ce qui la rend nécessaire.

## Critères d'acceptation

- [ ] `.env.example` dit que `GITHUB_TOKEN` est requis dès qu'un projet est en
      `autonomy: pr` ou `merge`
- [ ] `.env.example` dit que `GITHUB_REPO` ne sert qu'à `github-sync`
- [ ] Le fichier mentionne `github_remote` comme source du dépôt par projet
- [ ] `uv run pytest backend/tests/test_consignes_coherentes.py` passe

## Dépendances

Aucune.

## Estimation

Moins d'une journée.

## Risques

Aucun — le fichier n'est lu que par des humains, il n'est pas chargé.
