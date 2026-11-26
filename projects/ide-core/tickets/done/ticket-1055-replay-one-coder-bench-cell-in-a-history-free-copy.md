---
agent: codeur
created: 2026-11-26
depends_on:
- ticket-1053
- ticket-1054
estimated_days: 2
id: ticket-1055
pr_number: 1278
priority: medium
status: done
title: Replay one coder bench cell in a history-free copy
type: feat
---

# ticket-1055 — Rejouer une cellule du banc dans une copie sans historique

## Objectif

Un exécuteur qui rejoue une cellule (entrée, bras) : codeur, tests, reviewer, validateur, trois
tours au plus, et consigne une ligne reprenable.

## Contexte

ADR-095, conception §3, §5, §7. Modèle : `scripts/seconde_revue.py` (plafond, JSONL, reprise).
Le script importe en lecture seule `provider_pour_role`, `run_review`, `lire_verdict`, `run_validation` ;
jamais `Orchestrator`, `RunLock`, la livraison ni la base.

## Solution proposée

`scripts/banc_codeur.py` (commande) et `scripts/banc_codeur_cellule.py` (une cellule).
Résultats : `docs/essais/banc-codeur/resultats.jsonl`.

## Critères d'acceptation

- [ ] La copie se fait par `git archive base_sha`, extrait sous `~/.tessera/banc-codeur/<essai>/<cellule>/`
      (jamais sous `IDE_WORKTREES_DIR`), puis `git init` et un seul commit : un test montre que
      `git log --all` n'y rend qu'un commit et que le diff réel n'y est pas lisible.
- [ ] Le codeur reçoit le texte du ticket relu à `base_sha` (somme contrôlée contre le manifeste) ; reviewer,
      validateur et testeur sont ceux du manifeste temporaire, identiques pour tous les bras.
- [ ] Ni push, ni PR, ni `RunLock`, ni base SQLite : un test lance une cellule avec un provider doublé et constate
      qu'aucun de ces appels n'a lieu.
- [ ] Chaque ligne du JSONL porte les champs du §5 (tours, `approuve_t1`, `tests_verts`, coûts codeur et
      contrôles, jetons, durées, `etat`) et le `gel_sha256` du corpus.
- [ ] `--budget-usd` (vérifié avant chaque cellule), un plafond de 6 $ par cellule (`plafond_cellule`) et la
      reprise : une cellule déjà `ok` ne se rejoue pas, et un `gel_sha256` différent arrête le script.
- [ ] `tests_reference_verts` pose après coup les fichiers de test du vrai diff et se consigne à part ; une
      copie dont `uv sync` échoue se consigne `echec_env`.

## Ce que ça ne fait pas

- Ne lit pas les résultats et n'applique aucune règle de décision (ticket-1056).
- N'appelle aucun modèle réel dans ses tests.

## Dépendances

ticket-1053, ticket-1054.

## Estimation

Deux jours.

## Risques

Un test de 6 minutes par tour allonge l'essai : le script reste séquentiel et se reprend.