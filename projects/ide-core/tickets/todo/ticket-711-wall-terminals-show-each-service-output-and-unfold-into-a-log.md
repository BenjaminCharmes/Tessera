---
id: ticket-711
title: "Wall terminals show each service's last output and unfold into its log"
type: feat
status: todo
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
- Un écran mural par service : un fond noir, les 4 dernières lignes de
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
- [ ] Un test de l'écran mural : les 4 dernières lignes de `sortie` sont affichées, et une ligne « Error: … » porte la classe ou le style rouge
- [ ] Un test du panneau : le filtre « Erreurs » ne garde que les lignes d'erreur, et la recherche filtre sur le texte saisi
- [ ] Un test : un clic sur l'écran mural ouvre le panneau, et « Fermer » le referme
- [ ] Un test : un service `code_de_sortie: 1`, `arrete_a_la_main: false` rend sa baie en état « tombé » ; avec `arrete_a_la_main: true`, non
- [ ] Un test : une `AppEnCours` d'origine `externe` n'a pas d'écran mural
- [ ] `EnCoursView.test.tsx` rend l'écran « En cours » et y trouve l'écran mural d'un service lancé

## Ce que ça ne fait pas
- Pas de flux WebSocket des logs : l'interrogation existante suffit
- Ne change pas le nombre de lignes conservées
