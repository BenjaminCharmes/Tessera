---
id: ticket-049
title: "Git flow : branche develop entre les tickets et main"
type: chore
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-15
---

# ticket-049 — Git flow avec une branche `develop`

## Objectif

Insérer une branche d'intégration `develop` entre les branches de ticket et
`main` : chaque couple issue/PR cible `develop`, et `develop` est fusionnée
dans `main` quand l'ensemble est vert.

## Contexte

Aujourd'hui chaque branche de ticket part sur `main` et y retourne directement.
Deux conséquences :

- `main` reçoit du travail ticket par ticket, sans qu'on ait jamais vérifié que
  les tickets **fusionnés entre eux** tiennent. Chaque PR est verte isolément ;
  rien ne teste leur combinaison avant qu'elle n'atteigne `main`.
- Il n'existe aucun point où regarder « ce qui part à la prochaine release ».

En mode autonome le problème s'aggrave : l'orchestrateur peut produire
plusieurs branches de tickets d'affilée, chacune verte séparément.

## Solution proposée

### Flux

```
ticket-XXX-description  ──PR──▶  develop  ──PR──▶  main
        │                            │                │
    CI par PR                 CI d'intégration    release
```

- **`main`** — état publiable. Ne reçoit que des merges depuis `develop`.
- **`develop`** — intégration continue. Cible par défaut de toutes les PR de
  ticket.
- **`ticket-XXX-…`** — une par ticket, part de `develop`, y retourne.

### CI

`ci.yml` déclenche aujourd'hui sur `pull_request: branches: [main]`. Les PR
vers `develop` ne lancent donc **aucun check** — c'est le changement le plus
important du ticket, et le plus facile à oublier.

```yaml
on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main, develop]
```

### Backend

`GitWorkspaceService` capture sa ref de base au premier usage
(`rev-parse HEAD`) : il suivra donc naturellement `develop` si c'est la branche
courante. Aucun changement de code n'est requis — mais il faut un test qui le
confirme plutôt que de le supposer.

Le service de création de PR (`github_service`) cible en revanche `main` en
dur : la base doit devenir configurable, avec `develop` par défaut.

### Documentation

- `CLAUDE.md`, section Git — décrire le flux et la cible par défaut
- `.github/workflows/README.md` — la stratégie par phase de tickets y est
  périmée (elle parle encore des tickets 000–002)
- Le skill `ticket-workflow` doit brancher depuis `develop`

## Contraintes

1. **Ce ticket autorise la modification de `CLAUDE.md`** (règle 4), pour la
   section Git **et** pour la section « État actuel », périmée : elle affirme
   que tous les tickets sont dans `done/`, alors que 045 est en cours et 046 à
   049 sont en attente.
2. `develop` doit être créée depuis `main` avant toute retarget de PR.
3. Ne pas changer la branche par défaut du dépôt GitHub sans décision explicite
   — c'est un réglage à effet large (clones, liens, comparaisons).

## Critères d'acceptation

- [x] La branche `develop` existe sur `origin`, créée depuis `main`
- [x] `ci.yml` déclenche sur les PR vers `main` **et** vers `develop`
- [x] La création de PR cible `develop` par défaut, la base restant paramétrable
- [x] Un test couvre le fait qu'une branche de ticket part bien de la branche
      courante (`develop`) et non de `main`
- [x] `CLAUDE.md` décrit le flux `ticket → develop → main`
- [x] `CLAUDE.md` « État actuel » reflète les tickets réellement ouverts
- [x] `.github/workflows/README.md` ne décrit plus la stratégie périmée
- [x] Le skill `ticket-workflow` branche depuis `develop`

## Dépendances

Aucune. À coordonner avec [ticket-047](ticket-047-skills-locaux.md) : le skill
`ticket-workflow` décrit ce flux.

## Estimation

**1j**.

## Risques

- **Moyen** — une PR ouverte vers `main` pendant la bascule perd ses checks si
  `ci.yml` est modifié avant que `develop` n'existe. Faire les choses dans
  l'ordre : brancher `develop`, puis élargir la CI, puis retarger.
