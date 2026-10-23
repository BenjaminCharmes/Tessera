---
id: ticket-562
title: "The office sprites and a project room"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-561"]
estimated_days: 2
created: 2026-10-23
plan: true
---

# ticket-562 — Les sprites et la pièce d'un projet

## Objectif
Dessiner la pièce d'un projet : cinq postes, un personnage par poste occupé,
son écran, sa bulle et sa pastille de santé. C'est la brique que les tickets
563 à 566 complètent d'objets.

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md` ;
ADR-058. Maquette : `design/maquette/Bureau.dc.html` (pièces, postes) et
`design/maquette/Bureau-Compact.dc.html` (la rangée compacte du même projet).
La structure de la maquette fait foi ; ses couleurs deviennent des jetons.
Sélecteurs : ticket-561. Santé : `lib/santeAgent.ts` (ticket-549).

## Solution proposée
- `frontend/src/design/bureau/` : sprites SVG inline en pixels (`rect`,
  `shape-rendering: crispEdges`), un fichier par sprite (personnage, poste,
  écran, bulle, pastille). Aucune couleur brute : jetons `--sprite-*` dans le
  `@theme` de `index.css` ; états en `zinc`, `red`, `amber`, `green`, `blue`.
- `frontend/src/components/BureauView/Piece.tsx` et `PosteDeTravail.tsx` : une
  pièce par run, un poste par entrée de `postesDuRun`. Chaque poste est un
  `button` dont l'`aria-label` dit l'état en mots (« Codeur, travaille »).
- Animations `tape`, `lueur`, `flotte` en `@keyframes` dans `index.css`, sur
  `transform` et `opacity` seulement, coupées par `prefers-reduced-motion`.
- Un seul `setInterval` de 5 s pour toute la vue (hook `useSanteDuBureau`),
  qui alimente `santeAgent` ; aucun minuteur par sprite.
- Rendu compact (`Compact.tsx`) : la rangée d'un projet quand `modeCompact`.

## Critères d'acceptation
- [ ] Une pièce rend cinq postes, un `button` chacun, avec un `aria-label` qui nomme le poste et son état, et un test Testing Library le vérifie pour `occupe`, `fait` et `libre`
- [ ] La bulle et la pastille d'un poste reprennent le libellé de `santeAgent` (« travaille », « silencieux », « figé ? », « question »), et un test le vérifie avec une horloge simulée
- [ ] Dix pièces rendues ensemble produisent moins de 2 000 nœuds SVG, et un test les compte
- [ ] Le rendu monte un seul `setInterval` pour dix pièces, et un test le vérifie avec des minuteurs simulés
- [ ] `grep` ne trouve dans `design/bureau/` ni couleur hexadécimale ni famille Tailwind brute hors `zinc`, `red`, `amber`, `green`, `blue` ; les tons de peau, de cheveux et de dossier sont des jetons `--sprite-*`, et un test de source le vérifie
- [ ] Aucune propriété animée autre que `transform` et `opacity`, et chaque `@keyframes` du Bureau est neutralisé sous `prefers-reduced-motion`, et un test de source le vérifie
- [ ] Aucun fichier du diff ne dépasse 300 lignes, et le diff ne modifie aucun fichier de `backend/`
- [ ] `npm run test`, `tsc` et `eslint` passent

## Ce que ça ne fait pas
- Aucun des objets autour de la pièce : dossiers, courrier et baie (563), pause et réunion (564), tableau (565), colonne « À toi » (566).
- Ne remplace pas la vue par défaut : c'est le ticket-567.
- Ne montre aucun élément sans donnée réelle derrière lui (ADR-058).
