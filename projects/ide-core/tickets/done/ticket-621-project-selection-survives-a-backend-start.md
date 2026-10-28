---
id: ticket-621
title: "Selecting a project works even when the interface loaded before the backend"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-621 — Choisir un projet marche même si l'interface a chargé avant le backend

## Objectif
Qu'un clic sur un projet le sélectionne toujours, et qu'on puisse en choisir
un depuis la colonne latérale quand aucun n'est actif.

## Contexte
Le 28/10, au relancement de Tessera, cliquer une carte de la vue Projets ne
sélectionnait plus rien, et la vue Tickets affichait « Aucun projet
sélectionné » sans aucun moyen d'en choisir un.

Deux causes, reproduites avec Playwright sur l'app réelle :
- `useProjects` lit `/api/v1/projects` une seule fois. Si cette lecture échoue
  — le frontend est prêt avant le backend au démarrage —, la liste reste vide
  jusqu'au rechargement. Les cartes de la vue Projets viennent d'une autre
  lecture et s'affichent ; leur clic cherche le projet dans la liste vide et
  ne fait rien, sans erreur.
- Depuis le ticket-586, la colonne latérale n'a plus sa liste de projets. Sans
  projet actif, `ProjectHeader` n'affiche qu'un texte : le sélecteur
  n'apparaît que lorsqu'un projet est déjà choisi.

## Solution proposée
- `useProjects` relit la liste tant que la dernière lecture a échoué, à
  intervalle fixe.
- `SelecteurDeProjet` accepte l'absence de projet et s'affiche alors comme
  « Choisir un projet », sans l'action de retrait.
- `ProjectHeader` sans projet affiche ce sélecteur quand `onSelectProject` est
  fourni.

## Critères d'acceptation
- [x] Un test de `useProjects` vérifie qu'après une lecture en échec la liste est relue et se remplit
- [x] Un test de `ProjectHeader` vérifie que, sans projet et avec `onSelectProject`, on peut choisir un projet dans la liste
- [x] Un test de `SelecteurDeProjet` vérifie que, sans projet, l'action « Retirer ce projet de l'IDE… » n'est pas proposée

## Ce que ça ne fait pas
- Ne fusionne pas les deux lectures de la vue Projets (vue d'ensemble et liste) :
  c'est un sujet de l'audit sur la duplication.
