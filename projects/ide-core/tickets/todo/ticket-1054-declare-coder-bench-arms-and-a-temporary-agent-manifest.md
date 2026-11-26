---
id: ticket-1054
title: "Declare coder bench arms and a temporary agent manifest"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-26
---

# ticket-1054 — Déclarer les bras du banc et leur manifeste temporaire

## Objectif

Qu'un bras (modèle + prompt) se déclare dans un fichier de l'essai et se construise en provider
sans que `agents.json` ni `agents/prompts/` d'ide-core soient touchés.

## Contexte

ADR-095, conception §4. La seconde revue écrit déjà un `agents.json` temporaire puis appelle
`provider_pour_role` (ticket-844) ; on fait de même, pour le rôle `codeur`.

## Solution proposée

`scripts/banc_codeur_bras.py` : `Bras(id, modele, provider, prompt)`, `charger_bras(chemin)`,
`manifeste_temporaire(bras, projet) -> Path` (dossier temporaire avec `agents.json` et prompts).
Données : `docs/essais/banc-codeur/bras.json` (A, M, P) et `prompts/codeur-p.md`.

## Critères d'acceptation

- [ ] `bras.json` déclare A (modèle et prompt lus de `agents.json` et `agents/prompts/codeur.md` d'ide-core,
      copiés à la date du gel), M (`claude-opus-5-5`) et P (modèle d'A, prompt `codeur-p.md`).
- [ ] `manifeste_temporaire` écrit, dans un dossier neuf, un `agents.json` dont le rôle `codeur` est celui du
      bras et dont reviewer, validateur et testeur sont copiés à l'identique ; un test compare ces rôles à ceux d'ide-core.
- [ ] Le manifeste, le prompt et les skills du bras sont résolus dans le dossier temporaire : un test prouve
      qu'aucun fichier d'ide-core n'est ouvert en écriture (sommes avant et après).
- [ ] Aucun repli : un bras sans provider disponible lève une erreur nommée, consignée `indisponible` par l'exécuteur.
- [ ] `codeur-p.md` ne diffère de `codeur.md` que par un seul ajout, écrit avant toute mesure : lire « Ce que ça ne
      fait pas » et les ADR cités avant de coder, lancer les tests ciblés avant de rendre.
- [ ] `agents/prompts/`, `agents.json` et `backend/src/` n'apparaissent pas dans le diff.

## Ce que ça ne fait pas

- N'appelle aucun modèle ; ne construit aucune cellule.
- Ne décide pas de l'adoption d'un bras.

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

Le texte de la variante est un choix humain : le valider avant le gel (ticket-1058).
