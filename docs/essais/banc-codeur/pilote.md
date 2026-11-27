# Pilote du banc du codeur (ticket-1057)

Le pilote ne conclut rien sur les bras (ADR-095). Il mesure le coût et vérifie que le rejeu marche.

## Ce qui a tourné

Trois cellules sur neuf, toutes sur l'entrée `e58ba3643486` (ticket-968). Les six autres n'ont pas été jouées :
après 9,41 $ consignés, le garde-fou du banc refuse une cellule qui pourrait dépasser le plafond
de 15 $ (une cellule peut coûter jusqu'à 6 $). Le plafond est la règle, le pilote s'arrête là.

| Entrée | Bras | Modèle | Tours | Approuvé | Tests de la cellule | Tests de référence sur le code du codeur | Coût | Durée |
|---|---|---|---|---|---|---|---|---|
| e58ba3643486 | A | sonnet-5-5 | 1 | oui | verts | rouges | 1,35 $ | 17 min |
| e58ba3643486 | M | opus-5-5 | 3 | non | rouges | rouges | 4,76 $ | 22 min |
| e58ba3643486 | P | sonnet-5-5 | 3 | non | rouges | rouges | 3,30 $ | 40 min |

Total : 9,41 $ (sous les 15 $). La colonne « référence » dit si les tests de la vraie solution passent sur le code
écrit par le codeur ; l'approbation n'en dépend pas.

## Les trois entrées

Commande `reference` (vraie solution posée sur la copie de base, tests lancés) :

| Entrée | Ticket | Copie installée | Tests tournent | Référence |
|---|---|---|---|---|
| e58ba3643486 | ticket-968 | oui | oui | verte |
| 749247ecfa2d | ticket-967 | oui | oui | **rouge** : à remplacer avant de figer le corpus |
| f44fefc4eb1d | ticket-964 | oui | oui | verte |

Aucune entrée en `echec_env`. Pour les cellules jouées (e58ba3643486), la copie s'installe et les tests tournent
dans les trois bras.

## Coût

Une seule entrée jouée : les moyennes par bras sont des mesures uniques, pas des moyennes.

| Bras | Cellules | Coût moyen |
|---|---|---|
| A | 1 | 1,35 $ |
| M | 1 | 4,76 $ |
| P | 1 | 3,30 $ |
| Toutes | 3 | 3,14 $ |

Projection à 65 cellules (20 entrées x 3 bras + A2 sur 5) : 25 x 1,35 + 20 x 4,76 + 20 x 3,30 = 194,95 $,
près du double du plafond de 100 $.

## Taille du corpus

Coût par entrée sur les trois bras : 9,41 $. Avec A2 sur 5 entrées (6,75 $) :

- 16 entrées : 16 x 9,41 + 6,75 = 157,3 $
- 10 entrées : 10 x 9,41 + 6,75 = 100,9 $

Aucune taille de 16 à 20 ne tient sous 100 $ avec ces coûts. Les coûts de M et de P pèsent (cellules en trois tours,
non approuvées) ; une cellule par bras est trop peu pour dire s'ils sont représentatifs. Les options pour 1058 :
relever le plafond à environ 160 $, ou rester à 100 $ avec environ 10 entrées (hors de la fourchette 16 à 20 de
l'ADR), ou retirer A2 et jouer M sur une partie du corpus seulement. C'est une décision humaine avant le gel.

## Constats

- Le rejeu marche : copies sans historique, reprise par JSONL, plafond respecté.
- Durée : 17 à 40 min par cellule, soit 1 h 20 pour trois cellules en séquence ; 65 cellules prendraient plus de 20 h.
- Une interruption (redémarrage) laisse une copie à moitié faite ; la cellule se rejoue en entier à la reprise.
