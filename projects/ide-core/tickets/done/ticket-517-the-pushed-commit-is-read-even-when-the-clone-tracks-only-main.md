---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 0.5
id: ticket-517
pr_number: null
priority: high
status: done
title: The pushed commit is read from the remote even when the clone tracks only main,
  so an approved PR is merged
type: fix
---

# ticket-517 — Le commit poussé se lit même quand le clone ne suit que `main`

## Objectif
Qu'une PR approuvée et verte d'un projet cloné par Tessera soit mergée par le
CIWatcher, au lieu de rester ouverte avec « commit poussé inconnu ».

## Contexte
Depuis le ticket-492, le CIWatcher ne merge que si la tête de la PR est le
commit que la livraison a poussé. Ce SHA est lu par
`GitWorkspaceService.sha_distant`
(`backend/src/tessera/services/git_workspace.py`) avec
`git rev-parse refs/remotes/origin/<branche>`.

`backend/src/tessera/services/git_clone.py` clone avec `--depth=1`, ce qui
implique `--single-branch` : le refspec devient
`+refs/heads/main:refs/remotes/origin/main`. Un `git push` de la branche du
ticket ne crée alors aucune référence `refs/remotes/origin/<branche>`,
`sha_distant` renvoie `None`, et le CIWatcher refuse de merger.

Le 19/10, Devinoo : PR #70 (ticket-031) et PR #72 (ticket-032), approuvées et
vertes, sont restées ouvertes (« commit poussé inconnu ») et ont été mergées à
la main. En base, `pushed_sha` est vide pour ces deux runs, et renseigné pour
tous ceux de Kadoomi et d'ide-core, dont le refspec est complet. `portfolio` et
`benjamincharmes` avaient le même refspec réduit. Les quatre dépôts ont été
corrigés à la main (`git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"`).

## Solution proposée
1. `sha_distant` lit la vérité sur le distant quand la référence locale
   manque : `git ls-remote origin refs/heads/<branche>`. Il renvoie toujours
   `None` si le distant ne répond pas, et le CIWatcher reste fermé (ADR-039).
2. `git_clone.py` garde `--depth=1` mais ajoute `--no-single-branch`, ou
   rétablit le refspec complet juste après le clone.
3. Au démarrage, ou à la livraison, un dépôt dont `remote.origin.fetch` ne
   couvre pas `refs/heads/*` est signalé dans les logs du backend
   (`refspec_reduit`), avec le projet en cause.

## Critères d'acceptation
- [ ] Dans `git_workspace.py`, `sha_distant` renvoie le SHA de la branche distante quand `refs/remotes/origin/<branche>` n'existe pas, via `git ls-remote` (un test le vérifie sur un dépôt dont le refspec ne suit que `main`)
- [ ] Un test vérifie que `sha_distant` renvoie `None` quand le distant est injoignable
- [ ] Dans `git_clone.py`, un dépôt cloné par Tessera a `remote.origin.fetch` = `+refs/heads/*:refs/remotes/origin/*` (un test le vérifie)
- [ ] Un test vérifie que la livraison d'un dépôt au refspec réduit renseigne `pushed_sha`
- [ ] Les tests existants de `git_workspace` et de la livraison passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
`ls-remote` est un appel réseau : il ne sert qu'en repli, et une erreur rend
`None` (fermé), jamais une exception qui casserait la livraison.