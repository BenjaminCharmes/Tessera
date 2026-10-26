---
agent: codeur
created: 2026-10-23
depends_on:
- ticket-558
- ticket-562
estimated_days: 1
id: ticket-565
pr_number: null
priority: medium
status: done
title: The office day board
type: feat
---

# ticket-565 — Le tableau du jour

## Objectif
Afficher dans le Bureau la dépense du jour et le quota de la session et de la
semaine, avec leur heure de reprise, sans inventer ce qu'on ne sait pas.

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md`,
lignes « Tableau du jour ». Maquette : `design/maquette/Bureau.dc.html`.
`GET /usage/stats?days=7` rend `daily[]` avec `cost_usd` (le jour courant est
le dernier point, en UTC ; `days=1` est refusé en 422). `GET /usage/quota`
vient du ticket-558 et rend `{windows: {}}` tant qu'aucun relevé n'est venu.
Un graphique, s'il y en a un, vit sous `design/charts/` (ADR-047).

## Solution proposée
`frontend/src/components/BureauView/TableauDuJour.tsx`, avec un hook
`useTableauDuJour` : la dépense = `daily[-1].cost_usd`, le quota =
`windows.five_hour` et `windows.seven_day`. Une fenêtre absente s'affiche
« inconnu », jamais une barre à 0 %. Le jour est le jour UTC, dit dans
l'`aria-label`. Relecture toutes les 60 s et à chaque `run_closed`.

## Critères d'acceptation
- [ ] La dépense affichée est le `cost_usd` du dernier point de `daily`, et un test le vérifie
- [ ] Une réponse `daily` vide affiche 0, pas une erreur, et un test le vérifie
- [ ] Une fenêtre absente de `windows` affiche « inconnu » et aucune barre de progression, et un test le vérifie
- [ ] Une fenêtre présente affiche son `utilization` en pourcentage et son heure de reprise `resets_at`, et un test le vérifie pour `five_hour` et `seven_day`
- [ ] Le tableau se relit sur `run_closed`, et un test le vérifie avec un client simulé
- [ ] L'`aria-label` du tableau précise que le jour est en UTC, et un test le vérifie
- [ ] Aucune couleur hors `zinc`, `red`, `amber`, `green`, `blue` (ADR-026), et les graphiques éventuels sont sous `design/charts/` (ADR-047)
- [ ] Aucun fichier du diff ne dépasse 300 lignes, et le diff ne modifie aucun fichier de `backend/`
- [ ] `npm run test`, `tsc` et `eslint` passent

## Ce que ça ne fait pas
- Ne crée aucun endpoint : la dépense se lit dans `/usage/stats`, le quota dans `/usage/quota` (ticket-558).
- Ne notifie pas un quota bas : c'est le ticket-555.
- Ne convertit pas le jour UTC en jour local.