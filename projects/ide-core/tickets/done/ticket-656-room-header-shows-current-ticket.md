---
id: ticket-656
title: "Each Bureau room names the ticket it is working on"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-656 — La pièce dit quel ticket elle traite

## Objectif
Lire dans chaque pièce le numéro et le titre du ticket en cours.

## Contexte
Le 28/10 : la pile de dossiers ne montre que les tickets suivants. Un run d'un
seul ticket n'affichait donc le sien nulle part, et dans une file il fallait
ouvrir le fil pour savoir où elle en était.

## Solution proposée
`ticketEnCours` (`lib/bureau/ticketEnCours.ts`) lit l'identifiant dans l'état du
run, à défaut dans le run, et le titre dans le run, que le backend tient à jour à
chaque `ticket_status_changed`. L'en-tête de la pièce l'écrit à côté du nom du
projet, tronqué, le texte entier en infobulle. Aucune lecture des tickets par
pièce : elle ajouterait un minuteur à chacune.

## Critères d'acceptation
- [x] Un test de `ticketEnCours` vérifie le ticket d'un run seul avec son titre, le ticket courant d'une file, et l'absence de ticket

## Ce que ça ne fait pas
- Ne change pas la pile de dossiers, qui reste la liste des tickets suivants.
