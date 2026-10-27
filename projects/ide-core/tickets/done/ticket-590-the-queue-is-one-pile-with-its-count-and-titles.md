---
agent: codeur
created: 2026-10-26
depends_on:
- ticket-581
estimated_days: 0.25
id: ticket-590
pr_number: 663
priority: high
status: done
title: The queue is one pile of folders with its count, and its titles on hover
type: fix
---

# ticket-590 — La file est une seule pile, avec son nombre et ses titres

## Objectif
Le 26/10, la file ide-core comptait quinze tickets : la pièce affichait quinze
icônes orange côte à côte, sans rien dire. Benjamin : « les icônes dossier
orange qui ne display rien du tout ».

## Contexte
- `components/BureauView/Dossiers.tsx` rend un `Dossier` (sprite
  `design/bureau/Dossier.tsx`) par ticket restant, avec l'identifiant seul en
  `title` natif.
- La maquette (`design/maquette/Bureau.dc.html`, bouton `p.dossiersLabel`)
  dessine **une** pile : un à trois dossiers empilés selon le nombre, et le
  nombre écrit dessous.
- Les titres des tickets se lisent avec `useTickets` (`hooks/useTickets.ts`).

## Solution proposée
- Une seule pile : 1, 2 ou 3 dossiers empilés (3 au-delà de trois tickets),
  et le nombre de tickets restants écrit dessous.
- Au survol et au focus clavier, une infobulle liste les tickets restants
  dans l'ordre de la file : identifiant et titre, dix au plus, puis « et N
  autres ». Un titre introuvable laisse l'identifiant seul.
- Le libellé accessible reste « Tickets restants : N ».

## Critères d'acceptation
- [ ] Avec 15 tickets restants, la pièce rend 3 sprites `dossier` et le texte « 15 » ; un test le vérifie
- [ ] Avec 2 tickets restants, elle rend 2 sprites et « 2 » ; un test le vérifie
- [ ] Au focus de la pile, l'infobulle montre l'identifiant et le titre de chaque ticket, dans l'ordre de la file ; un test le vérifie
- [ ] Au-delà de dix tickets, l'infobulle en montre dix puis « et N autres » ; un test le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/`