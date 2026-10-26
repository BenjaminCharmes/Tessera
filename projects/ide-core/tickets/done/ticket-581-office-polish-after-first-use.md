---
agent: codeur
created: 2026-10-26
depends_on:
- ticket-567
estimated_days: 0.5
id: ticket-581
plan: true
pr_number: 656
priority: high
status: done
title: 'Office view polish after first use: no duplicate state, folder tooltips, one
  place for services, an honest unknown quota'
type: fix
---

# ticket-581 — Retouches du Bureau après le premier usage

## Objectif
Corriger ce que Benjamin a relevé en ouvrant le Bureau le 26/10, sans changer
la charte ni la maquette (`design/maquette/Bureau.dc.html`).

## Contexte et corrections
1. **État en double** : la bulle au-dessus du personnage (`design/bureau/Bulle.tsx`)
   écrit le mot de l'état (« travaille »), déjà écrit par la pastille du pied
   de la pièce. La maquette ne mettait dans la bulle qu'un signe : « … »
   (silencieux), « ? » (question), « ! » (figé ?), et rien quand l'agent
   travaille.
2. **Dossiers sans information** : la pile de dossiers
   (`components/BureauView/Dossiers.tsx`) ne dit pas quels tickets attendent.
   Chaque dossier porte en infobulle l'identifiant et le titre de son ticket,
   et la pile garde son libellé accessible.
3. **Curseur trompeur** : un élément qui n'a pas d'action au clic n'a pas
   `cursor-pointer` (le poste de l'agent en a un aujourd'hui sans action ; son
   action viendra au ticket-582).
4. **Services en double** : la rangée des services en haut de la vue
   (`ServicesLances` dans `components/SupervisionView/BureauConnecte.tsx`)
   répète la baie de serveurs de chaque pièce. Elle est retirée du Bureau
   (elle reste dans la vue Liste). Dans la baie
   (`components/BureauView/BaieDeServeurs.tsx`), chaque service tient sur une
   ligne : son nom et son voyant ; le détail (« pas lancé par l'IDE »,
   `design/etatDuService.ts`) passe en infobulle.
5. **Quota inconnu** : le SDK n'envoie de relevé de quota qu'à l'approche
   d'une limite ; sans relevé, `FenetreDeQuota.tsx` écrit « inconnu » deux
   fois. Afficher un tiret, avec en infobulle « Pas de relevé : le quota
   s'affiche quand l'abonnement en annonce un ».

## Critères d'acceptation
- [ ] `Bulle.tsx` ne rend rien pour un agent qui travaille, et rend « … », « ? » ou « ! » pour silencieux, question et figé ? ; un test le vérifie pour les quatre états
- [ ] Chaque dossier de `Dossiers.tsx` a un attribut `title` qui contient l'identifiant de son ticket, et un test le vérifie
- [ ] `BureauConnecte.tsx` ne rend plus `ServicesLances`, et `ListeView.tsx` le rend toujours ; un test le vérifie pour les deux vues
- [ ] Dans `BaieDeServeurs.tsx`, le texte de `etatDuService` est en `title` et n'est plus affiché sous le service, et un test le vérifie
- [ ] Sans relevé, `FenetreDeQuota.tsx` affiche « — » avec l'infobulle décrite, et un test le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/`