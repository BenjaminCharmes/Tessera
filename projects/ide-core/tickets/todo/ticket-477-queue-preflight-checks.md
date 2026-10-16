---
id: ticket-477
title: "A run is refused before its first ticket when delivery or tests cannot work"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
plan: true
created: 2026-10-16
---

# ticket-477 — Contrôles avant le départ d'une file

## Objectif

`POST /api/v1/orchestrator/run` refuse tout de suite, avec la liste des
manques, un run qui ne pourrait pas livrer ou tester, au lieu de le
découvrir après un ticket complet.

## Contexte

Vu plusieurs fois : curio (13/10, `github_remote` absent, ticket-001 codé
puis non livré), souhaito (16/10, `autonomy: merge` sans aucun workflow
GitHub Actions, « CI none » après un ticket complet), souhaito encore
(`pnpm` introuvable dans un script). Chaque fois, un ticket entier
(codeur, revues, PR, de 2 à 7 $) avant l'arrêt.

## Solution proposée

Avant de démarrer, pour le projet visé :
- `autonomy` ≥ `pr` et pas de `github_remote` : refus ;
- `autonomy: merge`, `merge_without_ci` absent ou faux, et aucun fichier
  `.github/workflows/*.yml` dans le dépôt : refus (« ajouter une CI ou
  déclarer merge_without_ci ») ;
- `test_command` déclaré : le premier mot de chaque segment `&&` doit être
  trouvable (`shutil.which` ou chemin existant), sinon refus avec le nom de
  la commande.

Le refus est une réponse 422 qui liste chaque manque ; `force: true` dans
la requête permet de passer outre.

## Critères d'acceptation

- [ ] Un test vérifie le refus 422 pour `autonomy: merge` sans workflow ni
      `merge_without_ci`
- [ ] Un test vérifie le refus pour `autonomy: pr` sans `github_remote`
- [ ] Un test vérifie le refus quand un segment du `test_command` commence
      par une commande introuvable, avec son nom dans la réponse
- [ ] Un test vérifie qu'un projet correct démarre comme avant
- [ ] Un test vérifie que `force: true` démarre malgré un manque
