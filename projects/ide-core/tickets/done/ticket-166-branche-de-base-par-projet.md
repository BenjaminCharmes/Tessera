---
id: ticket-166
title: "La branche de base est globale, et le projet n'a que main"
type: fix
status: done
pr_number: 10
priority: critical
agent: codeur
depends_on: ["ticket-159"]
estimated_days: 1
created: 2026-09-25
---

# ticket-166 — La branche de base est globale

## Objectif

Qu'un projet dont la branche de base n'est pas `develop` puisse être livré.

## Contexte

Premier run du banc d'essai après ticket-159 : approuvé en un tour, commit
écrit. Puis la livraison s'arrête.

```
Livraison interrompue : git command failed (code 128):
  git … rebase develop
  fatal: invalid upstream 'develop'
```

Le projet n'a que `main`. `github_base_branch` est un réglage **global**
(`config.py:65`, défaut `develop`) — juste pour ce dépôt-ci, faux pour tout
projet qui n'a pas la même convention de branches.

C'est la forme exacte qu'ADR-029 a écartée pour l'autonomie : « un réglage
global — le bon niveau dépend du dépôt ». La branche de base dépend du dépôt
au même titre, et pour la même raison. `PolitiqueRun` porte déjà les quatre
réglages d'`agents.json` qui bornent un run ; celui-ci en est un cinquième.

Second défaut, indépendant : l'erreur remontée est celle de git. `invalid
upstream 'develop'` ne dit ni que c'est un réglage, ni lequel, ni où le
changer. ADR-039 veut qu'une étape qui ne peut pas conclure dise pourquoi
en toutes lettres.

## Solution proposée

1. `PolitiqueRun` lit `base_branch` dans `agents.json`, `None` à défaut ; la
   livraison et le workflow l'utilisent au lieu du réglage global, qui reste
   le repli.
2. `rejouer_sur` vérifie que la base existe **avant** de rejouer, et lève une
   erreur qui nomme la branche et le réglage à écrire.

## Critères d'acceptation

- [ ] `PolitiqueRun.lire()` rend le `base_branch` déclaré, `None` sans lui
- [ ] Un `agents.json` illisible ou absent ne fait pas échouer la lecture
- [ ] La livraison rebase sur la branche du projet quand elle est déclarée,
      sur le réglage global sinon
- [ ] Rejouer sur une base inexistante lève une erreur qui **nomme la
      branche** et `base_branch`, pas `invalid upstream`
- [ ] `uv run pytest` et `uv run mypy src/` passent

## Dépendances

ticket-159, dont ce défaut prolonge le 4ᵉ critère : la livraison va plus loin
qu'avant, et bute un cran après.

## Estimation

Moins d'une journée.

## Risques

Un projet qui déclare une base inexistante échouera plus tôt, avec un message
clair au lieu d'un rebase qui tente. C'est l'effet recherché.
