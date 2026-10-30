---
id: ticket-710
title: "One server room per project, with a rack per service and its details on hover"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-30
---

# ticket-710 — Une salle par projet, une baie par service, son détail au survol

## Objectif
La vue « En cours » montre une salle par **projet** lancé, pas par processus.
Les salles occupent la largeur de l'écran, et chaque service s'y lit au survol.

## Contexte
Retour de Benjamin le 30/10 sur la vue livrée par les tickets 672 et 673. Curio,
seul projet lancé, s'affichait en deux salles (backend et frontend) : `SallesDesServeurs`
(`frontend/src/components/EnCoursView/SallesDesServeurs.tsx`) rend une `SalleDApp`
par élément de l'inventaire, donc par processus. Chaque salle prenait toute la
largeur pour n'en occuper qu'une petite partie. Le survol n'affichait rien.

Maquette : `projects/ide-core/design/maquette/Salle-des-serveurs-v2.dc.html`.

## Solution proposée
- Grouper les `AppEnCours` par `project_id` : une salle par projet, qui contient
  une baie par service, avec le nom du service et son premier port sur la baie.
- Afficher les salles en grille : deux colonnes à partir de 1280 px de large,
  une seule en dessous.
- Au survol ou au focus clavier d'une baie, une infobulle donne le pid, les
  ports, la mémoire et l'heure de démarrage. Ce sont les champs d'`AppEnCours`,
  rien d'inventé (ADR-058).
- La plaque de la salle porte le nom du projet, le nombre de services et la
  somme de leur mémoire.
- Ce qui existe est gardé : agents du produit (ticket-673), bouton d'arrêt,
  bascule Salles/Liste.

## Critères d'acceptation
- [x] `SallesDesServeurs.test.tsx` : deux `AppEnCours` du même `project_id` donnent une seule salle avec deux baies ; deux projets donnent deux salles
- [x] `SallesDesServeurs.test.tsx` : la plaque d'une salle affiche le nom du projet, « 2 services » et la somme des `memoire_mo`
- [x] `SallesDesServeurs.test.tsx` : le focus d'une baie affiche une infobulle (`role="tooltip"`) avec son pid, ses ports et sa mémoire
- [x] La grille des salles déclare deux colonnes au-delà de 1280 px et une en dessous ; un test vérifie la classe ou le style posé sur le conteneur
- [x] `EnCoursView.test.tsx` rend l'écran « En cours » avec un projet à deux services, et n'y trouve qu'une salle

## Ce que ça ne fait pas
- Pas d'écrans de journal : c'est le ticket-711
- Pas de poste de run : c'est le ticket-712

## Livraison
Implémenté à la main avec Benjamin, en direct sur un Vite de branche (5175), le 30/10. Écarts à la maquette validés en route : moniteurs accrochés au mur, journal sous la salle (un second clic le referme), agents du produit au modèle du Bureau (prénom, bulles, infobulle, clic vers le journal de leur service), sol posé dalle par dalle, bouche de VMC dont l'hélice suit la mémoire du projet. Les tests vivent dans `SallesDesServeurs.test.tsx`, qui rend l'écran « En cours » entier.
