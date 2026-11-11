---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 1
id: ticket-928
pr_number: null
priority: high
status: done
title: The secret read guard sees through device and UNC paths and refuses a Grep
  glob that can reach a guarded file
type: fix
---

# ticket-928 — La garde de lecture des secrets voit à travers `\\?\` et l'UNC local, et refuse un glob de `Grep` qui peut atteindre un fichier gardé

## Objectif

Qu'un agent ne lise plus le `.env` de Tessera, ni les autres fichiers gardés,
en changeant seulement l'écriture du chemin ou la forme du glob.

## Contexte

Audit de sécurité du 11/11, rejoué sur `origin/develop`, module
`backend/src/tessera/services/providers/garde_jetons.py` :

- **Préfixes de chemin Windows.** `_resoudre` (l. 83-100) développe `~` et les
  variables, puis appelle `Path.resolve()` ; `vise_le_env` (l. 103-106)
  compare par égalité. `resolve()` garde le préfixe `\\?\C:\…` et la forme
  `\\localhost\C$\…` : le chemin rendu n'est jamais égal à `C:\…\.env`, et un
  `Read` de `\\?\C:\…\tessera\.env` ou de `\\localhost\C$\…\tessera\.env`
  passe. `\\.\C:\…` est déjà refusé (résolu sans préfixe). Le même
  `_resoudre` sert à `Bash` (`_commande_vise_le_env`) et à `Glob`/`Grep` :
  corriger la fonction ferme les quatre outils.
- **Glob de `Grep`.** `motif_vise_le_env` (l. 109-128) exige que le dernier
  segment commence par un littéral (l. 117), et `_outil_vise_le_env`
  (l. 195-200) ne contrôle le dossier que **sans** `glob`. Un `Grep` sur la
  racine de Tessera avec `glob: "*env"`, `"{.env,x}"` ou `"[.]env"` passe et
  lit le fichier ; de même sur `frontend/` avec `"*.local"` pour les
  `.env*.local`. `Glob` seul ne rend que des noms : la règle « `*` seul ne
  refuse pas » y reste juste.

Côté écriture, ces formes échouent déjà fermées : `hors_perimetre`
(`backend/src/tessera/services/providers/perimetre.py`) compare par
`is_relative_to` et refuse un chemin préfixé.

ADR-031 vaut ici : la garde attrape une erreur, pas une évasion
(`python -c "open('../../'+'.env')"` passe toujours). Le ticket ferme des
formes de chemin et de glob, pas toute lecture.

## Solution proposée

- Dans `_resoudre`, sous Windows, ramener `\\?\X:\…`, `//?/X:/…`,
  `\\?\UNC\localhost\X$\…`, `\\localhost\X$\…` et `\\127.0.0.1\X$\…` à
  `X:\…` avant `resolve()`. Variante acceptable : comparer aussi par identité
  de fichier (`os.path.samefile` quand les deux existent).
- Pour `Grep` : si le dossier visé (`path`, ou le dossier de travail sans
  `path`) contient un fichier gardé **et** qu'un `glob` est fourni, refuser
  dès que ce glob, accolades développées (`{a,b}`), peut désigner le fichier
  par son nom ou son chemin relatif (`fnmatch`, sans tenir compte de la
  casse), quel que soit son premier caractère. Un glob qui ne peut pas le
  désigner (`*.py`) passe.
- Classe de la faille (leçon « une faille ferme toute sa classe ») : `Read`,
  `Bash`, `Glob` et `Grep` passent tous par `_resoudre`, et les trois cibles
  de `cibles` (l. 218-225) — `.env`, fichier du jeton, `.env*.local` —
  profitent de la même correction.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_garde_jetons.py` vérifie qu'un `Read` de
      `\\?\` suivi du chemin absolu du `.env` est refusé (sous Windows ;
      ignoré ailleurs).
- [ ] Un test vérifie qu'un `Read` de `\\localhost\<lecteur>$\…` vers le
      `.env` est refusé (sous Windows ; ignoré ailleurs).
- [ ] Un test vérifie qu'un `Grep` dont `path` est le dossier du `.env` est
      refusé avec chacun des globs `*env`, `{.env,x}` et `[.]env`.
- [ ] Un test vérifie qu'un `Grep` dont `path` est le dossier `frontend/`
      d'un `.env.local` gardé est refusé avec le glob `*.local`.
- [ ] Un test vérifie qu'un `Grep` sur le dossier du `.env` avec le glob
      `*.py` passe.
- [ ] Le diff ne modifie pas `backend/src/tessera/services/providers/perimetre.py`.

## Ce que ça ne fait pas

- Ne ferme pas la construction d'un chemin en deux temps
  (`D=../..; cat $D/.env`, `cat ../../.e''nv`) : ADR-031 ; le plafond réel est
  la portée du jeton et le compte dédié (ticket-915).
- N'ajoute aucun fichier gardé : c'est le ticket-929.

## Dépendances

Aucune.

## Estimation

Un jour.

## Risques

`garde_jetons.py` fait 257 lignes : si la normalisation et le contrôle du glob
le font dépasser 300, les extraire dans un module voisin. Un `Grep` large
(`*`) sur un dossier qui porte un secret sera refusé : c'est voulu.