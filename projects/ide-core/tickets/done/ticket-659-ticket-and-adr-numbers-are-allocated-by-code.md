---
agent: codeur
created: 2026-10-28
depends_on: []
estimated_days: 2
id: ticket-659
plan: true
pr_number: 748
priority: high
status: done
title: Ticket and ADR numbers are allocated by code, and a run renumbers what collides
  before delivery
type: feat
---

# ticket-659 — Les numéros de ticket et d'ADR attribués par le code

## Objectif
Qu'aucun ticket ni aucune ADR ne prenne un numéro déjà pris sur `develop` ou sur
une autre branche ouverte.

## Contexte
Un agent prend aujourd'hui « le plus grand numéro + 1 » sur sa propre branche.
`TicketService._next_n` (`services/ticket_service.py`) ne lit que l'arbre local.
Deux tickets de conception partis du même `develop` prennent donc les mêmes
numéros. Le 28/10, le 570 et le 576 ont tous deux créé 611 à 615 et l'ADR-061 ;
la résolution de conflit a écrasé l'ADR de l'un, et il a fallu tout renuméroter
à la main. Les tickets d'audit ont dû sauter à 650 pour laisser de la place.

## Solution proposée
- `scripts/prochain_numero.py` (ticket ou ADR) rend le plus grand numéro + 1, lu
  sur l'arbre, sur `origin/develop` et sur les branches `origin/ticket-*`. Les
  prompts de l'architecte et du codeur demandent de l'utiliser.
- Avant la livraison d'un run, une étape relève les tickets et les ADR que son
  diff ajoute. Si un numéro est déjà pris sur `origin/develop`, elle renumérote :
  nom du fichier, champ `id`, titre, `depends_on` et mentions dans les fichiers
  du diff. Elle journalise chaque renumérotation.

## Critères d'acceptation
- [ ] Un test de `scripts/prochain_numero.py` vérifie qu'un numéro présent seulement sur une branche `origin/ticket-*` est compté
- [ ] Un test de l'étape de livraison vérifie qu'un `ticket-611` ajouté par le diff, alors que `origin/develop` porte déjà un `ticket-611`, devient le prochain numéro libre, avec son fichier, son `id` et ses mentions dans le diff
- [ ] Un test vérifie la même renumérotation pour une ADR ajoutée à `memory/decisions.md` dont le numéro existe sur `origin/develop`
- [ ] Un test vérifie que chaque renumérotation écrit une ligne dans `memory/pipeline-log.md`

## Ce que ça ne fait pas
- Ne renumérote rien de ce qui est déjà mergé.
- Le skill `new-ticket` vit sous `.claude/` : y mentionner le script se fait à la main.