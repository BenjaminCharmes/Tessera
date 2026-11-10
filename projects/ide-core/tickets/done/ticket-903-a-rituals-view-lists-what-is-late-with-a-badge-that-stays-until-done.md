---
agent: codeur
created: 2026-11-10
depends_on:
- ticket-902
estimated_days: 1
id: ticket-903
pr_number: 1015
priority: high
status: done
title: A Rituals view lists what is late, with a rail badge that stays until done
type: feat
---

# ticket-903 — Une vue Rituels montre ce qui est en retard, avec une pastille qui reste jusqu'au « Fait »

## Objectif

Que Benjamin voie, sur n'importe quel PC où tourne Tessera, les actions
récurrentes en retard, et qu'il ne puisse pas les perdre d'un clic comme une
notification fermée.

## Contexte

Le ticket-902 sert `GET /api/v1/rituels`, `POST /api/v1/rituels/{id}/fait` et
`POST /api/v1/rituels/{id}/reporter`. Il manque l'écran. Maquette validée :
`projects/ide-core/design/maquette/Rituels.dc.html` (la vue) et
`Rituels-Alerte.dc.html` (la pastille). Benjamin a écarté le bandeau : la
pastille de l'onglet suffit, parce qu'elle ne part qu'au « Fait » ou au report.

## Solution proposée

- `"rituels"` rejoint `PANNEAUX` de `components/Sidebar/panels.ts` ; `NavRail`
  l'affiche dans le groupe Pilotage, après Supervision, avec une pastille ambre
  (ADR-026 : l'ambre pour une attente) portant le nombre de rituels
  `en_retard`, absente à zéro.
- Un hook `useRituels` lit `GET /api/v1/rituels` par `usePolling` (toutes les
  5 minutes, et à l'ouverture), expose la liste, `enRetard` et deux actions
  `fait(id)` / `reporter(id)` qui appellent la route puis relisent. Passer par
  le client HTTP existant (`lib/http.ts`), qui porte le jeton.
- `components/RituelsView/` rendu par `CenterView` pour ce panneau, d'après la
  maquette, pleine largeur : sections « À faire » (cartes : titre, depuis
  quand, rythme et durée, détail, phrase à dire à Claude avec « Copier »,
  un bouton « Ouvrir <projet> » par entrée de `projets` qui sélectionne ce
  projet dans Tessera, « Fait », « Reporter à demain »), « À venir » (une ligne
  par rituel, la `prochaine` échéance) et « Faits récemment ». Un `depasse`
  s'affiche en rouge. Le champ `erreur` de la réponse s'affiche en tête de vue.
- Couleurs en tokens de la charte, jamais en dur ; le violet seulement en fond
  du bouton « Fait ».

## Critères d'acceptation

- [ ] `frontend/src/components/Sidebar/panels.ts` contient `"rituels"`, et un
      test de `NavRail` vérifie que la pastille montre 2 pour deux rituels
      `en_retard` et n'existe pas pour zéro.
- [ ] Un test de `RituelsView` vérifie qu'un rituel `en_retard` est dans la
      section « À faire » et un rituel `a_venir` dans « À venir ».
- [ ] Un test vérifie qu'un clic sur « Fait » appelle
      `POST /api/v1/rituels/<id>/fait` puis relit la liste.
- [ ] Un test vérifie que « Copier » écrit la `phrase` du rituel dans le
      presse-papiers.
- [ ] Un test vérifie qu'un `erreur` non nul dans la réponse est affiché.
- [ ] Le diff ne modifie ni `rituels.md` ni aucun fichier sous `backend/`.

## Ce que ça ne fait pas

- Pas de bandeau sur les autres vues : écarté par Benjamin le 10/11.
- Pas de notification dans la cloche : ticket-904.
- Pas d'édition des rituels depuis l'écran.

## Dépendances

ticket-902 (les routes).

## Estimation

1 jour.

## Risques

- `navigator.clipboard` exige un contexte sécurisé : `localhost` et l'app Tauri
  le sont.