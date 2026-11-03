---
id: ticket-622
title: "The queue button counts only what is not queued yet, and the Bureau's mailbox, pile and rack become shortcuts"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-622 — Bouton de file juste, raccourcis et échelle du Bureau

## Objectif
Que le bouton de file dise ce qui reste à ajouter, et que les objets du Bureau
mènent là où on les attend.

## Contexte
Retours du 28/10, après avoir vu deux étages du Bureau :
- Sur la carte d'un projet dont la file tourne, « Ajouter à la file (n) » comptait
  tous les tickets à faire, y compris ceux déjà dans la file. Le bouton ne
  changeait jamais : on croyait que rien n'était parti, et on cliquait en boucle.
- La boîte aux lettres ne menait à la PR que par le petit numéro à côté d'elle.
- La pile de dossiers ouvrait le fil du run (vue Liste), alors que le bouton « Fil »
  le fait déjà : des dossiers évoquent les tickets.
- La baie de serveurs n'était pas cliquable.
- L'interrupteur faisait le tiers de la porte, et la porte était plus petite que
  les agents.

## Solution proposée
- `LancerFile` reçoit les tickets restants de la file en cours, les retire du
  compte et de l'ajout, et dit « Tout est dans la file » quand il n'en reste aucun.
- La boîte aux lettres ouvre sa PR quand son URL est connue.
- La pile de dossiers ouvre l'onglet Tickets du projet, comme la porte.
- La baie ouvre l'adresse qu'un service lancé a annoncée dans sa sortie ; sans
  adresse, elle reste un meuble.
- L'interrupteur passe à 6 × 9 px ; la porte est agrandie de moitié.

## Critères d'acceptation
- [x] Un test de `LancerFile` vérifie que seuls les tickets hors de la file sont comptés et ajoutés
- [x] Un test de `LancerFile` vérifie que « Tout est dans la file » remplace le bouton quand la file a tout
- [x] Un test de `BoiteAuxLettres` vérifie qu'un clic sur la boîte ouvre l'URL de la PR
- [x] Un test de `PorteEtPile` vérifie que la pile ouvre les tickets du projet
- [x] Un test de `BaieDeServeurs` vérifie que la baie ouvre l'adresse annoncée, et reste un groupe sans elle
- [x] `adresseDeLApp` a son test : adresse lue malgré les codes ANSI, rien pour un service arrêté

## Ce que ça ne fait pas
- Ne dessine pas les rôles absents du Bureau (plan, documentation, résolveur) : ticket à part.
- Ne fait pas suivre à la salle de pause la CI d'une PR une fois la file passée au ticket suivant : ticket à part.
