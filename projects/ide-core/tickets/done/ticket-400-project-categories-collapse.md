---
agent: codeur
created: 2026-10-12
depends_on:
- ticket-399
estimated_days: 0.5
id: ticket-400
pr_number: null
priority: medium
status: done
title: Project categories collapse in the sidebar and the projects view, and a collapsed
  category shows how many projects it holds
type: feat
---

# ticket-400 — Les catégories de projets se replient

## Objectif

Réduire une catégorie dont on n'a pas besoin, sans perdre de vue ce qu'elle
contient.

## Contexte

Demande de Benjamin (2026-10-12). La barre latérale
(`frontend/src/components/Sidebar/ProjectNav.tsx`) range les projets par
catégorie (`grouperParCategorie`, ticket-175), et la vue « Projets »
(`ProjetsView`, ticket-399) affiche les mêmes groupes en sections. Avec cinq
catégories et quatorze projets, tout est toujours déplié.

## Solution proposée

1. Le titre de chaque catégorie devient un bouton (`aria-expanded`) qui
   replie ou déplie le groupe, avec un chevron qui tourne.
2. Repliée, la catégorie affiche à droite de son titre le nombre de ses
   projets (badge `zinc`). Une info-bulle (`title`) le dit en toutes lettres
   et nomme les projets : « 3 projets : demineur, serpent, cookie_clicker ».
3. L'état replié de chaque catégorie est mémorisé dans `localStorage` (clé
   `tessera.categories-repliees`), partagé entre la barre latérale et la vue
   « Projets ». Chaque lecture et chaque écriture est protégée par un
   `try/catch` : sans stockage disponible, tout reste déplié.
4. La catégorie qui contient le projet actif ne se replie jamais seule : on
   la voit toujours. Si l'utilisateur la replie lui-même, elle reste repliée,
   mais le projet actif reste affiché sous le titre.
5. Une recherche active dans la vue « Projets » déplie l'affichage des
   catégories qui ont des résultats, sans modifier l'état mémorisé.

## Critères d'acceptation

- [ ] Un test de `frontend/src/components/Sidebar/ProjectNav.test.tsx` vérifie qu'un clic sur le titre d'une catégorie masque ses projets, et qu'un second clic les rend visibles
- [ ] Un test de `frontend/src/components/Sidebar/ProjectNav.test.tsx` vérifie qu'une catégorie repliée affiche le nombre de ses projets, et une info-bulle qui en donne le nombre et les noms
- [ ] Un test de `frontend/src/components/Sidebar/ProjectNav.test.tsx` vérifie que l'état replié est relu depuis `localStorage` au montage, et qu'un `localStorage` qui lève une exception laisse tout déplié sans erreur
- [ ] Un test de `frontend/src/components/Sidebar/ProjectNav.test.tsx` vérifie que le projet actif reste visible quand sa catégorie est repliée
- [ ] Un test de `frontend/src/components/ProjetsView/ProjetsView.test.tsx` vérifie qu'une section repliée dans la vue « Projets » se déplie quand une recherche y trouve un résultat, sans changer l'état mémorisé

## Dépendances

ticket-399 (la vue « Projets » et ses sections).

## Estimation

0,5 jour.

## Ce que ça ne fait pas

- Ne permet pas de réordonner les catégories.