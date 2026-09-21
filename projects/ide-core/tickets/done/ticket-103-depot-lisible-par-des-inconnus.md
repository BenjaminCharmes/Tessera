---
id: ticket-103
title: "Le dépôt peut être lu par des inconnus"
type: docs
status: done
pr_number: 100
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-21
---

# ticket-103 — Le dépôt peut être lu par des inconnus

## Objectif

Qu'un lecteur extérieur n'apprenne rien qu'il ne devrait pas, et ne lise rien
de faux sur ce que le produit fait.

## Contexte

Le dépôt va passer en public. Deux familles de défauts s'y opposent, trouvées
par un audit.

### 1. Des données de clients dans des fichiers versionnés

- `backend/tests/test_pr_selon_la_forge.py` portait une URL d'infrastructure
  interne — `integration.interne.aws.cld.<client>.com` — et un
  compte Azure DevOps réel
- `ticket-081` et `ticket-085` nommaient deux clients
- `ProjectHeader.test.tsx` portait un chemin de machine avec un nom de client
- plusieurs tickets portaient un chemin personnel `/Users/<prénom>/`

Aucun identifiant, aucun jeton : ce ne sont pas des secrets techniques. Mais un
hostname d'infrastructure interne publié sur GitHub est de la reconnaissance
offerte, et nommer ses clients relève d'une question contractuelle.

### 2. La documentation décrit un produit qui n'existe plus

- `frontend/README.md` est le **template Vite intact** — le même défaut que
  ticket-100 a corrigé sur le titre et le favicon, resté ici parce qu'il ne
  contenait pas l'ancien nom. Une substitution en masse ne voit pas un défaut
  générique, seulement un défaut nommé.
- La référence API du `README.md` annonce 30 endpoints pour ~59 réels, et en
  documente un qui n'existe plus (`PATCH /tickets/:tid/status`).
- `.github/workflows/README.md` décrit le déclencheur **d'avant** ticket-095 —
  « push sur toutes branches » — c'est-à-dire la cause exacte du double run
  qui a épuisé les minutes. Il liste 4 jobs sur 5.
- `LLM_MAX_BUDGET_USD` est documenté à `1.0` ; ticket-102 l'a passé à `2.0`.
- Quatre variables ne sont pas documentées, dont `STATIC_TOKEN`, qui exige un
  `Authorization: Bearer` sur **toutes** les requêtes quand elle est définie.
- `CLAUDE.md` affirme « Pas d'authentification », ce que `STATIC_TOKEN`
  dément. Sous-déclarer une protection est le mauvais sens de l'erreur.
- Le frontend est annoncé à « 260 tests » ; il y en a 400.

## Solution proposée

1. Remplacer toute donnée de client par une valeur neutre, en gardant la forme
   testée : un GitLab auto-hébergé à sous-domaines profonds reste un GitLab
   auto-hébergé à sous-domaines profonds.
2. Écrire un vrai `frontend/README.md`.
3. Corriger `.github/workflows/README.md` : déclencheur réel et cinq jobs.
4. Regénérer la table des endpoints du `README.md` depuis `openapi.json`,
   documenter les variables manquantes et corriger les chiffres.
5. Corriger la phrase de `CLAUDE.md` sur l'authentification. **Ce ticket
   autorise explicitement cette modification** (règle 5).

**Hors périmètre** : l'historique git n'est pas réécrit. Les anciens commits
gardent leurs mentions ; c'est un choix assumé, la réécriture changeant tous
les SHA pour un gain nul dès lors qu'il ne s'agit pas de secrets. Le choix de
licence et le passage en public sont un ticket distinct.

## Critères d'acceptation

- [ ] `git grep` sur les noms de clients et les chemins personnels ne renvoie
      plus rien dans les fichiers suivis
- [ ] `frontend/README.md` ne contient plus « This template provides »
- [ ] `.github/workflows/README.md` décrit `push: [main]` et les cinq jobs
- [ ] La table des endpoints du `README.md` ne documente aucun endpoint absent
      de l'API, et n'omet aucun endpoint réel
- [ ] `README.md` documente `STATIC_TOKEN`, `DIALOGUE_TIMEOUT_S`,
      `GITHUB_BASE_BRANCH` et `IDE_DB_PATH`
- [ ] `README.md` annonce `LLM_MAX_BUDGET_USD` à `2.0` et le bon nombre de
      tests frontend
- [ ] `CLAUDE.md` ne dit plus qu'il n'y a pas d'authentification
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Anonymiser un test peut lui retirer ce qu'il testait. Les URLs de forge sont
choisies pour leur **forme** — sous-domaines profonds, chemin `/gitlab/`,
compte dans l'URL Azure — et les valeurs de remplacement la conservent.
