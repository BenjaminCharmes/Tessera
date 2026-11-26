---
agent: codeur
created: 2026-11-26
depends_on: []
estimated_days: 1
id: ticket-1053
pr_number: 1275
priority: medium
status: done
title: Freeze the coder bench corpus with base commit and ticket text
type: feat
---

# ticket-1053 — Figer le corpus du banc du codeur

## Objectif

Un manifeste qui dit, pour chaque ticket rejoué, le commit de base et le texte du ticket
à ce commit, et qui se vérifie par une somme.

## Contexte

ADR-095 et `design/banc-codeur/conception.md` §2. Modèle : `scripts/seconde_revue_corpus.py`
(ADR-079). Le module vit sous `scripts/`, n'importe rien de `tessera`, n'est jamais importé par le produit.

## Solution proposée

`scripts/banc_codeur_corpus.py` : types `Entree` et `Corpus` (champs du §2), `somme_gel`,
`charger`, `verifier`, et une commande `proposer` qui lit `git log` de `develop` et écrit les candidats.
Données dans `docs/essais/banc-codeur/corpus.json`.

## Critères d'acceptation

- [ ] Chaque entrée porte `base_sha` (premier parent du squash), `ticket_chemin` (trouvé par
      `git ls-tree -r <base_sha>`) et `ticket_sha256` du texte lu à `base_sha`, frontmatter retiré ;
      une fonction rend ce texte par `git show base_sha:ticket_chemin`.
- [ ] Un ticket absent à `base_sha` (créé par le squash lui-même) est écarté, avec son motif.
- [ ] Les exclusions de la conception §2 s'appliquent : `preuve_reelle`, compte agent, `agents.json`,
      `.github/`, hooks, frontend, diff sans test, hors de 30 à 600 lignes ajoutées.
- [ ] `somme_gel` porte sur les entrées non `pilote` et ne dépend pas de leur ordre ; `verifier`
      refuse un fichier dont la somme ne correspond pas, ou de moins de 16 entrées hors pilote.
- [ ] Un test sur un dépôt git temporaire montre que le texte relu à `base_sha` est celui d'avant
      une modification du ticket au commit suivant.
- [ ] Aucun fichier sous `backend/src/` ni `agents.json` n'est modifié.

## Ce que ça ne fait pas

- Ne rejoue rien et n'appelle aucun modèle.
- Ne gèle pas le corpus de l'essai : le gel se fait dans le ticket-1058, après le pilote.

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

Les squashs d'avant le 05/11 ont pu déplacer leur ticket entre dossiers : l'entrée sans chemin à la base est
écartée, pas devinée.