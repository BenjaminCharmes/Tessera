---
id: ticket-146
title: "Savoir avant le clic si un projet déclare des services"
type: fix
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-145"]
estimated_days: 1
created: 2026-09-23
---

# ticket-146 — Savoir avant le clic, pas après

## Objectif

Qu'un projet sans services déclarés n'affiche pas de bouton du tout, au lieu
de le faire disparaître au moment où on clique dessus.

## Contexte

**Signalé au premier essai sur un autre projet que `ide-core`.** Cliquer
« Lancer » sur `fluentdb` produit un `409` dans la console du navigateur, et
à l'écran : **le bouton disparaît**. Rien n'explique pourquoi.

C'est le code de ticket-138 : sur un message contenant « déclare aucun
service », `useServices` passe `declare: false`, et `BoutonServices` rend
`null`. L'intention — ne pas proposer de lancer ce qui ne peut pas l'être —
était juste ; le moment est faux.

La cause de fond est une erreur de conception : **`GET /services` ne liste que
les services qui tournent.** L'IDE ne peut donc pas savoir, au chargement, si
un projet est lançable. Il affiche le bouton partout, et n'apprend l'absence
de déclaration qu'en échouant.

## Solution proposée

`GET /projects/{id}/services` rend les services **déclarés**, chacun avec son
état courant :

- déclaré et lancé → `en_cours: true`, son `pid` ;
- déclaré et pas lancé → `en_cours: false`, `pid: null` ;
- rien de déclaré → liste vide.

Le bouton n'apparaît alors que si la liste est non vide, dès le premier
rendu, et ne disparaît plus jamais sous le curseur. Un 409 ne peut plus
survenir par ce chemin ; s'il survient quand même — manifeste modifié entre
temps — l'erreur s'affiche **sans** faire disparaître le bouton.

`pid` devient nullable dans le contrat, côté Python et côté TypeScript.

## Critères d'acceptation

- [ ] Un test vérifie que `GET /services` liste un service déclaré mais non
      lancé, avec `en_cours: false` et `pid: null`
- [ ] Un test vérifie que la liste reste vide pour un projet sans déclaration
- [ ] Un test vérifie qu'un service lancé garde son `pid` et `en_cours: true`
- [ ] Un test frontend vérifie qu'aucun bouton ne s'affiche quand la liste
      est vide, **sans avoir cliqué**
- [ ] Un test frontend vérifie qu'un échec au lancement affiche l'erreur et
      **laisse le bouton en place**
- [ ] `useServices` ne déduit plus `declare` d'un message d'erreur
- [ ] `uv run pytest`, `uv run mypy src/`, `npm run typecheck`,
      `npm run lint`, `npm run test` et `npm run build` passent
- [ ] Vérifié en vrai : `fluentdb` n'affiche aucun bouton, `ide-core` si

## Dépendances

ticket-145.

## Estimation

1 jour.

## Risques

Déduire un état d'une **chaîne de message** était le vrai défaut : le texte
change, la traduction change, et la condition casse en silence. Le remplacer
par une donnée du contrat est ce qui empêche le problème de revenir sous une
autre forme.
