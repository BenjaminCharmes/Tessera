# Charte — Tessera

Validée par Benjamin le 2026-10-14, d'après l'audit des neuf onglets.
Maquettes : `design/maquette/Charte.dc.html` (règles, composants) et
`Cadre.dc.html` (cadre commun) ; les vues par onglet dans `Fichiers`,
`Historique`, `Agents`. ADR-026 reste la règle des couleurs ; ce fichier la
précise.

## Couleurs — un rôle chacune

| Rôle | Valeur | Usage |
|---|---|---|
| fond | zinc-950 / `#0f0f11` | centre des vues |
| rail | `#121214` | barre de navigation |
| surface | zinc-900 / `#18181b` | colonne, tuiles, en-têtes de tableau |
| surface-haute | zinc-800 / `#27272a` | ligne choisie, champs, filets forts |
| trait | zinc-700 / `#3f3f46` | bordures de contrôles |
| texte | zinc-200 / `#e4e4e7` | texte principal |
| texte-doux | zinc-400 / `#a1a1aa` | secondaire, légendes |
| identité | violet-500 | onglet actif, barre de titre, action principale — en fond ou en barre, jamais en texte (ADR-026) |
| en cours | blue | run, service vivant |
| réussi | green | approuvé, mergé, tests ok |
| attention | amber | plusieurs tours, avertissement |
| échec | red | bloqué, refusé, erreur |

## Texte — six tailles

| Nom | Taille | Usage |
|---|---|---|
| titre-vue | 20 px / 600 | titre d'un détail (run, ticket, agent) |
| chiffre | 18 px / 600 | valeur d'une tuile |
| corps | 13 px / 400 | texte courant, lignes, boutons |
| bande | 12 px / 600, majuscules espacées | titre d'une bande d'en-tête |
| code | 12 px monospace | ids de ticket, branches, chemins, commandes, journal |
| légende | 11 px / 400 | métadonnées, en-têtes de tableau |

Le monospace est réservé à ce qui se copie. Les noms de rôles, de projets et
de services s'écrivent en police normale.

## Composants

- **Bande d'en-tête** : 40 px (`BAND`), barre violette de 3 px puis titre
  en `bande` ; à droite, le sélecteur de vue s'il y en a un. Même hauteur
  dans la colonne et au centre.
- **Sélecteur de vue** : groupe à fond surface, l'option active en
  surface-haute. Toute alternative de vue d'un onglet passe par lui.
- **Boutons** : un seul bouton **plein** (violet) par vue, l'action
  principale ; les autres sont **bordés** (trait) ou **discrets** (texte
  doux). Un arrêt est bordé de rouge, jamais plein. Hauteur 30 px (26 en
  colonne).
- **Pastille d'état** : fond teinté à 12 % de la famille de l'état, texte
  clair de la même famille, rayon 4 px, toujours un mot (jamais la couleur
  seule). Même composant dans Kanban, Historique, Supervision, En cours.
- **Listes et tableaux** : lignes de 36 px, en-tête en légende majuscule,
  filet zinc-800, ligne choisie sur fond surface-haute (pas de bordure
  violette dans une liste), montants alignés à droite.
- **États** : un **vide** dit quoi faire ensuite ; un **chargement** montre
  la forme du contenu ; une **erreur** offre toujours une sortie
  (« Réessayer »).

## Cadre commun

- Navigation regroupée : Pilotage, Projet, Outils (ticket-426). Les
  réglages (notifications, plafonds de dépense) vivent derrière un bouton
  Réglages en bas du rail, pas dans l'en-tête de colonne.
- En-tête de colonne : le nom du projet (sélecteur) et une pastille d'état
  s'il y a un run ; les actions du projet sur la ligne suivante. Une
  information secondaire (« ce projet fait tourner l'IDE ») passe en
  infobulle.
- Journal du pipeline : **repliable**, réduit par défaut à une ligne (le
  dernier évènement et une pastille d'activité), déplié à la demande ; l'état
  replié/déplié est mémorisé.
