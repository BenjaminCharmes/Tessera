---
id: ticket-260
title: "Delivery waits for CI checks to register before reading an absent CI as none"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-30
---

# ticket-260 — La livraison laisse aux checks le temps d'apparaître

## Objectif

Qu'un projet en `autonomy: merge` doté d'une CI merge vraiment ses PR quand la
CI passe au vert.

## Contexte

Constaté sur la PR #130 (ticket-253) le 2026-09-30, et déjà sur la PR #119 le
2026-09-29. L'événement `livraison_done` enregistré :

```
"etapes": ["rebase sur develop", "PR #130 ouverte", "CI : none"],
"arret": "CI none : la PR #130 reste ouverte."
```

La CI de la PR a pourtant tourné et fini verte trois minutes plus tard.

`LivraisonService._attendre_la_ci` (`services/livraison.py`) interroge
`etat_ci` **immédiatement** après l'ouverture de la PR. À cet instant GitHub n'a
encore enregistré aucun check : l'état agrégé vaut `none`, que la boucle traite
comme un verdict final (seul `pending` la fait attendre). Résultat : sur ce
dépôt, le niveau `merge` d'ADR-029 ne merge jamais.

ADR-029 reste juste : **l'absence de signal n'est pas un signal favorable**. Le
défaut est de lire l'absence avant que le signal ait pu exister.

## Solution proposée

- Ajouter à `LivraisonService` un délai de grâce `grace_ci_s` (constante de
  module, défaut 120 s, injectable au constructeur comme `intervalle_ci_s`).
- Dans `_attendre_la_ci`, tant que le temps écoulé est inférieur à ce délai,
  `none` se traite comme `pending` : on dort et on réinterroge. Passé le délai,
  `none` redevient un verdict et la livraison s'arrête comme aujourd'hui.
- La borne totale `_ATTENTE_CI_MAX_S` ne change pas et englobe le délai de
  grâce.
- Commentaire de la constante : dire pourquoi elle existe (les checks
  n'apparaissent qu'après l'ouverture de la PR), et renvoyer à ADR-029.

## Critères d'acceptation

- [ ] Un test montre que si `etat_ci` rend `none` puis `passing`, la livraison
      merge la PR (avec un `_dormir` factice, sans attente réelle).
- [ ] Un test montre que si `etat_ci` rend toujours `none`, la livraison
      s'arrête avec un `arret` qui contient `none`, une fois le délai de grâce
      écoulé.
- [ ] Un test montre que `failing` reçu pendant le délai de grâce arrête la
      livraison immédiatement, sans attendre la fin du délai.
- [ ] `LivraisonService.__init__` accepte un paramètre `grace_ci_s`.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Backend uniquement.

## Risques

- Un projet **sans** CI et sans `merge_without_ci` attendra désormais 120 s de
  plus avant de rendre la main : c'est le prix d'une lecture fiable, et
  `merge_without_ci: true` (ADR-045) existe pour ce cas.
