---
id: ticket-161
title: "La CI ne tourne plus : la faire tourner sur un runner local"
type: chore
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-24
---

# ticket-161 — La CI ne tourne plus : la faire tourner sur un runner local

## Objectif

Que les PR retrouvent des checks verts sans consommer de minutes GitHub.

## Contexte

Le dépôt est repassé en privé le 2026-09-23 (ticket-160). Les minutes GitHub
Actions incluses pour les dépôts privés sont épuisées : la PR #1 n'a déclenché
**aucun** run, et `gh run list` est vide alors que le workflow est actif, les
Actions autorisées et le déclencheur `pull_request` correct.

Ce n'est pas un défaut de la CI, c'est une facturation. Mais l'effet est le
même : plus aucun signal sur une PR, et la livraison automatique en
`autonomy: merge` ne peut plus conclure, ADR-029 et ADR-030 exigeant une CI
verte. Le quota ne revient pas avant le mois prochain.

Un runner **self-hosted** ne consomme aucune minute incluse, y compris sur un
dépôt privé. L'avertissement de GitHub sur les runners self-hosted vise les
dépôts **publics**, où une PR venue d'un fork ferait tourner du code
arbitraire sur la machine : ce dépôt est privé et n'accepte de PR que de son
propriétaire.

Deuxième défaut, indépendant et découvert en chemin : `make verify` ne lance
pas `npm run lint`, que la CI lance. « verify vert » ne voulait donc pas dire
« CI verte », ce qui est précisément la promesse de cette cible.

## Solution proposée

1. `runs-on` des quatre jobs non-macOS devient `${{ vars.CI_RUNNER ||
   'ubuntu-latest' }}`. Le dépôt bascule d'un côté ou de l'autre en changeant
   une variable, sans toucher au fichier — le retour au runner GitHub quand le
   quota revient ne demande alors rien à personne.
2. Les étapes qui supposent Linux sont gardées : `--with-deps` de Playwright,
   le script `bash` de `detecter`, et les deux actions de commentaire de
   couverture, qui sont cosmétiques et n'ont pas à faire rougir un run.
3. Le job `tauri` reste sur `macos-latest` : `cargo check` a besoin d'une
   chaîne Rust absente de cette machine. Il est déjà conditionné au changement
   de `frontend/src-tauri/`, donc rare.
4. `make verify` gagne `npm run lint`.

## Critères d'acceptation

- [ ] `runs-on` des jobs `backend`, `frontend`, `e2e` et `detecter` lit
      `vars.CI_RUNNER` et retombe sur `ubuntu-latest` si elle est absente
- [ ] `--with-deps` n'est passé à Playwright que sur Linux
- [ ] L'étape `detecter` déclare `shell: bash`
- [ ] Les deux étapes de commentaire de couverture ne tournent que sur Linux
- [ ] `make verify` lance `npm run lint`
- [ ] Un runner est enregistré sur le dépôt et une PR obtient des checks verts
      — c'est le seul critère qui prouve quoi que ce soit

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un runner hors ligne met les jobs en file d'attente sans fin, au lieu de les
faire échouer. C'est le prix du choix par variable : la sortie de secours est
de vider `CI_RUNNER`, et elle ne demande pas de PR.

Le runner exécute le code du dépôt sur la machine de l'utilisateur, sans
isolation. Acceptable ici parce que ce code est déjà celui qu'on lance à la
main dix fois par jour ; ça ne le resterait pas si le dépôt redevenait public.
