---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.5
id: ticket-922
pr_number: null
priority: high
status: todo
title: "Agents cannot read the frontend's local env files of Tessera"
type: fix
---

# ticket-922 — Aucun agent ne lit les `.env*.local` du frontend de Tessera

## Objectif

Fermer la lecture, par un agent, des fichiers d'environnement locaux du
frontend de Tessera, qui peuvent porter le jeton de l'API.

## Contexte

`services/providers/garde_jetons.py` refuse à tout agent la lecture de deux
fichiers : le `.env` de Tessera (ADR-053) et le fichier du jeton de session
(ADR-081). Depuis le 09/11, le backend tourne avec `STATIC_TOKEN`, et une
copie de ce jeton vit dans `frontend/.env.local` (gitignoré) pour les sessions
de développement. Le frontend ne lit pas ce fichier : le jeton lui arrive par
le fragment `#jeton=` (`lib/auth.ts`).

Aucune garde ne couvre ce fichier. Un agent d'ide-core, qui tourne dans le
checkout de Tessera, le lit d'un simple `Read`, et appelle ensuite toute
l'API. Même classe que les deux fichiers déjà gardés : un fichier local de
Tessera qui porte un jeton.

Vite charge `.env.local` et `.env.<mode>.local` : tous ces fichiers sont de la
même classe.

## Solution proposée

- `hook_refus_env_tessera` refuse aussi, avec un message propre
  (`ENV_LOCAL_REFUS`, même ton que les deux autres), les fichiers
  `frontend/.env.local`, `frontend/.env.development.local` et
  `frontend/.env.production.local` à la racine de Tessera (le dossier de
  `Settings.env_file`), résolus une fois comme les deux autres.
- Mêmes voies que pour le `.env` : `Read`, `Grep`/`Glob` (chemin, motif,
  dossier parent en recherche), `Bash` (chemin nommé, motif, recherche
  récursive sur un dossier qui le contient).
- Le `.env.local` d'un **projet** n'est pas concerné : seul celui du frontend
  de Tessera l'est.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_garde_jetons.py` vérifie qu'un `Read` de
      `frontend/.env.local` de Tessera est refusé avec le message dédié.
- [ ] Un test vérifie qu'une commande `Bash` `cat frontend/.env.local` et une
      recherche récursive `grep -r TOKEN frontend` lancées depuis la racine de
      Tessera sont refusées.
- [ ] Un test vérifie que `frontend/.env.development.local` est refusé.
- [ ] Un test vérifie que le `.env.local` d'un dossier de projet sous
      `projects/` passe.
- [ ] `backend/src/tessera/services/providers/garde_jetons.py` reste sous
      300 lignes.

## Ce que ça ne fait pas

- Ne supprime pas `frontend/.env.local` : c'est à Benjamin de décider s'il
  lit le jeton autrement.
- Attrape une erreur, pas une évasion (même plafond que les deux autres
  fichiers, ADR-031) : le vrai plafond est le compte agent (ADR-083).

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Une recherche récursive depuis la racine de Tessera (`grep -r x .`) sera
refusée, comme elle l'est déjà pour le `.env` : rien de nouveau.
