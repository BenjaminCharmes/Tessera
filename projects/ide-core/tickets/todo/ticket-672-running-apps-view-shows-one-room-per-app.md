---
id: ticket-672
title: "The running apps view shows one server room per app, with its state only"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-10-29
---

# ticket-672 — La vue « En cours » montre une salle des serveurs par app

## Objectif
Qu'une app lancée ait sa salle des serveurs dans « En cours », avec ce que
Tessera sait déjà d'elle et rien d'autre.

## Contexte
La maquette (étape 0 de
`docs/superpowers/specs/2026-10-29-salle-des-serveurs-design.md`) a fixé deux
choses le 29/10 :

- **La direction artistique est celle du Bureau** : pixel art en SVG
  `crispEdges`, 3 px par pixel, les mêmes tailles de sprite et le même zoom que
  les pièces de `BureauView`, l'en-tête de salle de `Salle`.
- **Le décor n'est pas celui d'un bureau.** Une première version reprenait
  fenêtres, plante, étagère et porte en bois : on lisait un bureau, pas une
  salle des serveurs. Les sprites de bureau (`SkyWindow`, `Plante`, `Etagere`,
  `Cadre`, `Bibliotheque`, `Porte`, `TableauBlanc`, `Poste`…) n'y entrent pas.

## Solution proposée
La maquette de référence est `projects/ide-core/design/maquette/Salle-des-serveurs.dc.html` :
elle fixe le décor et la disposition, pas les échelles, qui suivent celles du Bureau.

Une salle par entrée de `useAppsEnCours` (`AppEnCours`), avec ses ports, sa
mémoire et son démarrage, et l'état de ses services (`ServiceActif`).

Le décor est une salle technique, dessinée par de nouveaux sprites sous
`design/bureau/` :
- une **baie haute par service** déclaré : façade à grille d'aération, un
  voyant d'état par baie (`TON_VOYANT`, comme `Baie`) ;
- un **faux plancher à dalles** (carrés réguliers, quelques dalles perforées)
  à la place du parquet ;
- un **chemin de câbles** au plafond à la place des plafonniers ;
- un **climatiseur de salle** (armoire à grilles) et un **extincteur** ;
- une **porte coupe-feu** métallique avec son lecteur de badge.

Le mobilier suit ADR-058 : il se dessine toujours, sans voyant ni animation ;
seul le voyant d'une baie rend un état. Les nouvelles teintes (murs gris
froid, dalles, métal) sont des jetons `--sprite-*` du `@theme`.

La vue Liste existante reste dans le sélecteur.

## Critères d'acceptation
- [ ] La vue rend une salle par app de `useAppsEnCours`, et aucune quand la liste est vide, avec un test Testing Library
- [ ] Chaque salle affiche le nom du projet, les ports, la mémoire et l'heure de démarrage de l'app, lus de `AppEnCours`
- [ ] Une salle dessine une baie par service de l'app, et un test vérifie qu'un service `en_cours: false` donne un voyant différent d'un service qui tourne
- [ ] Les sprites `Climatiseur`, `CheminDeCables`, `Extincteur` et `PorteCoupeFeu` existent sous `design/bureau/`, et la salle n'utilise ni `SkyWindow`, ni `Plante`, ni `Porte`, ni `Etagere` (test de rendu par `data-sprite`)
- [ ] Les teintes nouvelles sont des jetons `--sprite-*` déclarés dans `index.css`, et le test existant `design/bureau/sources.test.ts` passe
- [ ] Aucun agent n'est dessiné : un test affirme qu'une salle ne contient aucun sprite de personnage

## Ce que ça ne fait pas
- Ne lit aucun fichier d'activité, ne dessine aucun agent : c'est ticket-673.
- Ne remplace pas la vue Liste.
- Ne touche pas aux sprites du Bureau.
