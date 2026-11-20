# Maquette de Tessera

Une seule maquette vivante : un canvas unique, étendu en place, dont ce dossier
est la source exacte. Toute évolution d'interface ajoute ou modifie un fichier
ici, puis republie ce même canvas ; on ne crée pas de canvas par évolution
(sauf exploration jetable entre plusieurs directions, qui entre ici une fois le
choix fait). L'adresse du canvas n'est pas écrite ici : il vit sur un compte
qui n'est pas le compte personnel du propriétaire, et ce dépôt est public.

## D'où vient la maquette

Elle se dessine avec le développeur, hors pipeline, dans l'éditeur de
maquettes de Claude : un fichier `.dc.html` par écran, versionné ici. Un agent
du produit n'a pas accès à cet éditeur et ne la produit pas.

## Comment la lire

Un fichier `.dc.html` est du HTML ordinaire avec des styles en ligne, plus
quelques balises propres à l'éditeur (`<x-dc>`, `<sc-for>`, `<sc-if>`, une
valeur entre doubles accolades) et une classe `Component` qui fournit les
données d'exemple. Il ne s'ouvre pas seul dans un navigateur : il se **lit**
comme référence. `Composants.dc.html` est statique (aucune donnée liée) et
s'ouvre aussi tel quel.

## Ce qui fait foi

- **La structure** : l'ordre des blocs, les tailles, les espacements et les
  états (vide, chargement, erreur, sélection, etc.) se reproduisent tels quels.
- **Les couleurs deviennent des tokens** : chaque couleur en dur de la
  maquette est remplacée par le token correspondant de la charte
  (`memory/design.md`, `@theme` de `index.css`). Aucune valeur en dur n'entre
  dans le code.
- **Les textes d'exemple sont des données**, pas du contenu à recopier.

## Publication

Le canvas est publié depuis ce dossier, avec deux exceptions de nommage :
`Charte.dc.html` y porte le nom `Main.dc.html`, que l'éditeur exige pour
l'écran d'entrée, et les trois fichiers de `coup-de-pinceau/` sont publiés à
plat sous les noms `Pinceau-Choisir.dc.html` (`Main`), `Pinceau-Tickets.dc.html`
et `Pinceau-Projets.dc.html`. Le canvas porte sept rangées : charte, vues,
Bureau, Salle des serveurs, Rituels, mise en ligne, composants. Les fichiers
marqués « non publié » restent ici sans entrer dans le canvas.

## Les écrans

Pages de 1440 px de large, sauf mention. « En vigueur » : l'écran existe dans
`frontend/src/` aujourd'hui.

| Fichier | Écran | En vigueur dans l'app |
|---|---|---|
| `Charte.dc.html` | charte : couleurs, texte, boutons, pastilles, listes, états | oui (`design/ui/`) |
| `Cadre.dc.html` | cadre commun : rail, colonne, journal repliable | oui |
| `Fichiers.dc.html` | vue Fichiers : éditeur vide, diff du ticket | oui |
| `Historique.dc.html` | vue Historique | oui |
| `Agents.dc.html` | vue Agents : fiche, comparer | oui |
| `coup-de-pinceau/Main.dc.html` | choisir un projet (vues de projet sans projet) | oui (`ChoixDuProjet`) |
| `coup-de-pinceau/Tickets.dc.html` | kanban en français, projet actif visible | oui |
| `coup-de-pinceau/Projets.dc.html` | cartes de projet égales | oui |
| `Bureau.dc.html` | Bureau des agents : une pièce par projet | oui |
| `Bureau-Compact.dc.html` | Bureau compact, une rangée par projet au-delà de six | **non implémenté** : seule la bascule Liste / Bureau existe |
| `Notifications.dc.html` | cloche : historique du jour et réglages | oui |
| `Bureau-vivant.dc.html` | Bureau animé, interactif (les boutons « Démo » et le panneau « Qui fait quoi » n'existent que dans la maquette ; dans l'app, les événements réels déclenchent les scènes) | oui |
| `Salle-des-serveurs-v2.dc.html` | En cours : une salle par projet | oui |
| `Salle-des-serveurs-v2-journal.dc.html` | journal d'un service, déplié | oui |
| `Salle-des-serveurs-v2-tessera.dc.html` | salle Tessera, toujours allumée | oui |
| `Rituels.dc.html` | vue Rituels | oui |
| `Rituels-Alerte.dc.html` | pastille ambre du rail et entrée de la cloche | oui |
| `MettreEnLigne-Carte.dc.html` | bouton sur la carte et confirmation | oui |
| `MettreEnLigne-Deroule.dc.html` | étapes et leurs sept états | oui |
| `MettreEnLigne-Detail.dc.html` | enregistrements DNS, clé à créer, Relancer | oui |
| `Composants.dc.html` | composants, 1440 × 7332 : jetons, boutons, champs, navigation, cartes, badges, modales, toasts, tableau, états, journal, graphiques, sprites ; chaque brique cite son fichier de l'app | — |
| `Salle-des-serveurs.dc.html` | première version de la salle des serveurs | non publié : remplacée par la v2 |

## Explorations closes, non reprises dans le canvas

- Salle des serveurs, première version : fichier gardé, remplacé par la v2.
- Tesselles candidates (ticket-100) : six marques, la première retenue.
- Atelier des sprites : les sources vivent dans `../atelier-sprites/`, plus
  récentes que toute copie publiée ; le canvas n'en montre qu'un échantillon
  dans `Composants.dc.html`.
- Guide d'utilisation de l'ancien nom du produit : page HTML ordinaire, pas une
  maquette.

## Écarts connus entre l'app et la maquette

La maquette dit l'intention ; ces écarts ne sont pas des erreurs à corriger
sans ticket. `Composants.dc.html` les détaille brique par brique.

- Bouton plein : `#7c3aed` et rayon de 5 px dessinés ; violet-500 et 4 px dans
  l'app.
- Fond : `#0f0f11` au centre et `#121214` au rail dans la charte ; l'app pose
  zinc-900 sur la racine et le rail, zinc-950 sur le journal et les champs.
- Rail : 96 px dessinés, 100 px dans l'app ; l'élément actif est un anneau
  violet dans la maquette, une barre violet-400 dans l'app.
- Bande d'en-tête : 12 px majuscules et barre de 3 px dessinées ; `RegionTitle`
  écrit en casse normale, barre de 2 px (la fenêtre Mettre en ligne suit la
  maquette).
- Cartes de projet : rayon de 10 px et 196 px de haut dessinés ; rayon de 2 px
  et hauteur au contenu dans l'app.
- Fenêtre Mettre en ligne : 480 px dessinés, 34 rem dans l'app.
- Statut d'un ticket : fonds pleins -900 dans l'app, pastille à 12 % dans la
  charte.
- Étapes de mise en ligne : « déjà là » et « ton action requise » ont une
  nuance dessinée que l'app ne reprend pas.
- Toasts, menu de catégorie, puces de filtre, compteurs : dans l'app seulement,
  dessinés d'après le code dans `Composants.dc.html`.
- États vide, chargement, erreur : encadrés dans la charte, sans cadre dans
  l'app.
- Modale de retrait d'un projet : bouton de confirmation rouge plein, contraire
  à « un arrêt n'est jamais plein ».
- Tableau des runs : la charte fixe des lignes de 36 px et des montants à
  droite ; l'app laisse la hauteur à `py-2`.

## Historique des lots

- **Charte et cadre** (2026-10-14) : `Charte`, `Cadre` et les vues par onglet
  `Fichiers`, `Historique`, `Agents`, validés avec la charte `memory/design.md`.
- **Mettre en ligne** (ticket-472).
- **Bureau des agents** (tickets 549, 550) et **notifications** (ticket-554).
- **Bureau vivant** (tickets 595 à 603, validé le 27/10).
- **Rituels** (tickets 902, 903) : vue et pastille ambre de l'onglet, qui reste
  jusqu'au « Fait ». Pas de bandeau.
- **Salle des serveurs** (ticket-672, puis v2).
- **Coup de pinceau** (ticket-735, audit du 02/11/2026) : sept constats dans
  `coup-de-pinceau/canvas.json`.
- **Composants** (2026-11-13) : le canvas devient unique ; `Composants.dc.html`
  est construit depuis le code de l'app.
