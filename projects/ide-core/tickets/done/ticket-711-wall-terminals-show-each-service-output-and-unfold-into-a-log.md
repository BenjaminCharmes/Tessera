---
id: ticket-711
title: "Wall terminals show each service's last output and unfold into its log"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-710"]
estimated_days: 1
created: 2026-10-30
---

# ticket-711 — Des écrans muraux montrent la sortie de chaque service, et se déplient en journal

## Objectif
Dans chaque salle, un écran par service lancé par Tessera affiche ses dernières
lignes de sortie. Un clic l'ouvre en journal complet. Un service tombé se voit.

## Contexte
`GET /api/v1/projects/{id}/services` (`backend/src/tessera/routers/services.py`, `lister`)
rend déjà, pour chaque service lancé par l'IDE, `sortie` (les 200 dernières
lignes, `LIGNES_CONSERVEES` dans `process_registry.py`), `en_cours`,
`code_de_sortie` et `arrete_a_la_main`. La salle n'en montre rien.

Maquettes : `projects/ide-core/design/maquette/Salle-des-serveurs-v2.dc.html`
(les écrans) et `projects/ide-core/design/maquette/Salle-des-serveurs-v2-journal.dc.html`
(le panneau).

## Solution proposée
- Un écran mural par service : un fond noir, les 5 dernières lignes de
  `sortie` en police mono, l'état en haut. Il se rafraîchit au même rythme que
  l'inventaire de la vue.
- Une ligne qui contient `error`, `exception`, `traceback` ou `fatal` (sans
  tenir compte de la casse) s'affiche en rouge. Une ligne qui contient `warn`
  s'affiche en ambre (ADR-026).
- Un clic sur l'écran ouvre un panneau latéral : toutes les lignes, numérotées,
  avec un filtre « Tout » / « Erreurs », un champ de recherche, une case
  « Suivre la fin » et un bouton « Copier ».
- Un service à `code_de_sortie` non nul, sans `arrete_a_la_main`, a sa baie au
  voyant rouge et sa salle encadrée de rouge.
- Un processus `externe` n'a pas d'écran : Tessera n'a pas sa sortie (ADR-058).

## Critères d'acceptation
- [x] Un test de l'écran mural : les 5 dernières lignes de `sortie` sont affichées, et une ligne « Error: … » porte la classe ou le style rouge
- [x] Un test du panneau : le filtre « Erreurs » ne garde que les lignes d'erreur, et la recherche filtre sur le texte saisi
- [x] Un test : un clic sur l'écran mural ouvre le panneau, et « Fermer » le referme
- [x] Un test : un service `code_de_sortie: 1`, `arrete_a_la_main: false` rend sa baie en état « tombé » ; avec `arrete_a_la_main: true`, non
- [x] Un test : une `AppEnCours` d'origine `externe` n'a pas d'écran mural
- [x] `EnCoursView.test.tsx` rend l'écran « En cours » et y trouve l'écran mural d'un service lancé

## Ce que ça ne fait pas
- Pas de flux WebSocket des logs : l'interrogation existante suffit
- Ne change pas le nombre de lignes conservées

## Livraison
Implémenté à la main avec Benjamin, en direct sur un Vite de branche (5175), le 30/10. Écarts à la maquette validés en route : moniteurs accrochés au mur, journal sous la salle (un second clic le referme), agents du produit au modèle du Bureau (prénom, bulles, infobulle, clic vers le journal de leur service), sol posé dalle par dalle, bouche de VMC dont l'hélice suit la mémoire du projet. Les tests vivent dans `SallesDesServeurs.test.tsx`, qui rend l'écran « En cours » entier.
