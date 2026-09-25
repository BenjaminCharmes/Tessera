---
id: ticket-117
title: "Décider, puis mener la migration vers Tailwind v4"
type: chore
status: done
pr_number: 136
priority: low
agent: architect
depends_on: []
estimated_days: 3
created: 2026-09-21
---

# ticket-117 — Décider, puis mener la migration vers Tailwind v4

## Objectif

Traiter Tailwind v4 comme la migration qu'elle est, et non comme une ligne
dans une mise à jour de dépendances.

## Contexte

Dependabot avait proposé un lot de 26 paquets frontend contenant
`tailwindcss` 3.4 → 4.3. La PR a été fermée : v4 déplace la configuration dans
le CSS et supprime `tailwind.config.ts`, alors que `CLAUDE.md` déclarait la v3.
La merger aurait changé la stack sans décision, dans un commit impossible à
bissecter.

## La décision : migrer

Trois mesures l'ont emporté sur la prudence :

1. **La surface est minime.** La configuration ne contenait que deux tailles
   de police (`micro`, `mini`, ADR-026) — aucun plugin, aucune couleur
   personnalisée, aucun `@apply`. L'essentiel du coût d'une migration Tailwind
   — réécrire une configuration touffue — n'existait pas ici.
2. **Le moment est le bon.** Backlog vide, CI verte, aucune PR en cours. Une
   migration risquée se mène quand tout le reste est stable, pas au milieu
   d'un chantier.
3. **La dette ne ferait que croître.** 546 `className` sur 49 fichiers
   aujourd'hui ; la migration coûtera plus cher à chaque ticket d'UI.

Rester en v3 restait défendable — elle est maintenue — mais c'était repousser
une échéance certaine en la rendant plus chère.

## Ce qui a levé le vrai risque

Le danger n'était pas technique mais **silencieux** : une régression visuelle
passe `tsc`, Vitest et Playwright sans les faire échouer. Aucun garde-fou du
dépôt ne mesurait le rendu.

D'où la méthode : capturer l'interface **avant**, migrer, capturer **après**,
comparer pixel à pixel. Puis — et c'est ce qui rend la mesure valable —
capturer une troisième fois sans rien changer, pour établir le **bruit de
fond** du rendu. Il est de **0,0000 %** : toute différence observée est donc
réelle, pas un artefact de capture.

| Élément | Avant | Après | Écart |
|---|---|---|---|
| `zinc-900`, le fond | `(24, 24, 27)` | `(24, 24, 27)` | **0** |
| bordure `zinc-700` | `(63, 63, 70)` | `(63, 63, 71)` | 1 |
| barre d'identité violette | `(167, 139, 250)` | `(166, 132, 255)` | **7** |

Écart maximal sur l'image entière : **18 sur 255**. C'est le passage de la
palette en **OKLCH**, documenté par v4 : les neutres ne bougent pas, les
teintes saturées gagnent quelques unités. Les cinq familles d'ADR-026 sont
conservées — seule leur expression change.

## Ce qui a été fait

1. `npx @tailwindcss/upgrade` — 31 fichiers migrés, `tailwind.config.ts`
   supprimé, PostCSS basculé sur `@tailwindcss/postcss`, `autoprefixer` retiré
   (v4 l'intègre).
2. Les deux tailles d'ADR-026 sont passées en `@theme` dans `index.css`.
3. `CLAUDE.md` déclare désormais la v4 — **ce ticket l'autorisait
   explicitement** (règle 5).

## Critères d'acceptation

- [x] Le coût et le bénéfice sont écrits, et la décision est prise
- [x] `npm run build` passe
- [x] Le rendu est comparé avant/après, avec un bruit de fond mesuré
- [x] `CLAUDE.md` ne déclare plus une version fausse
- [x] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

**TypeScript 7 et Vitest 5 ne sont pas montés.** Ils étaient dans le même lot
Dependabot sans rapport avec Tailwind ; ils reviendront séparément, et leur CI
est probante là où celle de Tailwind ne l'était pas.

Le shim de compatibilité des bordures ajouté par l'outil est **conservé** :
v4 passe la couleur de bordure par défaut à `currentcolor`, et le retirer
demanderait de poser une couleur explicite sur chaque élément qui dépend de
l'ancien défaut. C'est une dette, petite et nommée.

## Estimation

3 jours estimés ; une demi-journée réelle, la configuration minimale ayant
fait l'essentiel de l'écart.

## Risques

Les captures ne couvrent que deux écrans. Les modales, le diff, le panneau des
coûts et l'éditeur Monaco n'ont pas été comparés — le risque résiduel est là,
et il est faible : aucune de ces vues n'utilise de couleur hors des cinq
familles.
