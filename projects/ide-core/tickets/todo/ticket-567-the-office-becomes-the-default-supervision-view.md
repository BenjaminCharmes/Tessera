---
id: ticket-567
title: "The office becomes the default supervision view"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-562", "ticket-563", "ticket-564", "ticket-565", "ticket-566"]
estimated_days: 1.5
created: 2026-10-23
plan: true
---

# ticket-567 — Le Bureau devient la vue par défaut

## Objectif
Assembler le Bureau, en faire la vue par défaut de Supervision et laisser la
vue Liste dans le sélecteur, sans perdre aucune fonction de l'actuelle.

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md` ;
ADR-058. Maquettes : `design/maquette/Bureau.dc.html` (au plus 6 projets avec
un run) et `design/maquette/Bureau-Compact.dc.html` (au-delà).
`SupervisionView/index.tsx` fait 266 lignes ; le plafond est de 300
(ticket-545). Fonctions à garder : cartes de run et chrono, fil, rangement un
à un et par lot, services.

## Solution proposée
- `components/BureauView/index.tsx` assemble les pièces (562), objets (563,
  564), tableau (565) et colonne (566) ; `modeCompact` (561) choisit la
  rangée compacte, les projets sans run s'ajoutant en bas « au repos ».
- Le corps actuel de `SupervisionView/index.tsx` (la Liste) passe tel quel
  dans `SupervisionView/ListeView.tsx`, qui garde `RunCard`, `MenuFermer`,
  `ServicesLances`, `Chrono` et `issueDuRun`, que le Bureau réutilise sans les
  recopier. `SupervisionView/index.tsx` **se réduit** à un sélecteur Bureau /
  Liste qui rend l'une des deux vues ; le Bureau est le défaut.
- `SupervisionView.test.tsx` rend désormais `ListeView` (changement d'import et
  de composant rendu), parce que `index` rend le Bureau par défaut : ses
  assertions sur la Liste (`Run ticket-001 sur ide-core`, `attend une réponse`,
  `bloqué`, `Services lancés`…) ne changent pas. Les tests de `CenterView` et
  `App` moquent `./SupervisionView` en entier : ils ne sont pas concernés.
- Un clic sur une pièce ouvre le fil du run ; le rangement un à un et par lot
  reprend `fermerRuns` de `useSupervision`.
- Une seule source par run : le Bureau et la Liste lisent le même store
  (ADR-034).

## Critères d'acceptation
- [ ] Sans choix préalable, Supervision rend le Bureau, et un test le vérifie
- [ ] Le sélecteur bascule vers la Liste, et un test le vérifie : après le clic, les cartes de la Liste sont rendues
- [ ] Les tests de `SupervisionView.test.tsx` rendent `ListeView` et leurs assertions sont inchangées : `git diff` n'y montre que l'import, le composant rendu et d'éventuelles lignes ajoutées, aucune assertion retirée ni modifiée
- [ ] Avec 6 projets qui ont un run le Bureau rend des pièces, avec 7 il rend des rangées compactes, et un test le vérifie
- [ ] En compact, un projet sans run apparaît « au repos » après les autres, et un test le vérifie
- [ ] Ranger une pièce, et ranger par lot, appelle `fermerRuns` comme la Liste, et un test le vérifie
- [ ] Le chrono et le fil d'un run sont accessibles depuis le Bureau, et un test le vérifie
- [ ] Un même run montre la même issue et le même état dans le Bureau et dans la Liste, et un test le vérifie
- [ ] Aucun fichier du diff ne dépasse 300 lignes, `SupervisionView/index.tsx` fait moins de lignes qu'avant (266), et le diff ne modifie aucun fichier de `backend/`
- [ ] `npm run test`, `tsc`, `eslint` et `npm run build` passent

## Ce que ça ne fait pas
- Ne supprime pas la vue Liste.
- Ne crée aucun objet de la pièce : tout vient des tickets 562 à 566.
- Ne change ni le store de run, ni les endpoints.
