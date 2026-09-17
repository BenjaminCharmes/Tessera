---
id: ticket-067
title: "Consolidation visuelle — une palette à rôles, une échelle de texte, un jeu d'icônes"
type: refactor
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-065]
estimated_days: 2
created: 2026-09-17
---

# ticket-067 — Consolidation visuelle

## Pourquoi

L'UI a été construite ticket par ticket, et chaque feature a choisi ses
couleurs au moment où elle était écrite. Le résultat mesuré :

- **8 familles de couleurs** — `red`, `amber`, `green`, `blue`, `emerald`,
  `purple`, `orange`, `yellow`. `green` et `emerald` disent la même chose ;
  `amber`, `orange` et `yellow` aussi.
- **3 tailles de texte en dur** (`text-[9px]`, `text-[10px]`, `text-[11px]`) à
  côté de l'échelle Tailwind.
- **13 fichiers** portent encore des glyphes ou emoji comme affordances :
  `⚡ ✅ ⚠ ✕ ↗ ◈ █ ●`.

Personne n'a choisi huit couleurs. C'est de l'accrétion — le même défaut que
les cinq glyphes de la barre latérale corrigés par ticket-065, qui a d'ailleurs
**aggravé le contraste** : la barre est propre, et `ProjectNav` juste à côté
affiche toujours `◈`.

## Ce que ce ticket n'est pas

**Pas une refonte.** L'allure actuelle est validée. On ne change ni la mise en
page, ni le thème sombre, ni la densité. On supprime l'incohérence, à
apparence générale constante.

## Décision

**Cinq familles, un rôle chacune** — aucune couleur ne partage un emploi :

| Famille | Rôle |
| --- | --- |
| `zinc` | neutre, surfaces, texte, métadonnées |
| `red` | échec, blocage, audit refusé |
| `amber` | attente humaine, vigilance, en revue |
| `green` | succès, approuvé, terminé |
| `blue` | activité en cours, tour d'agent |

`emerald` fusionne dans `green`, `orange` et `yellow` dans `amber`. `purple`
disparaît : il servait aux badges GitHub, qui sont des **métadonnées**, pas un
état — ils passent en `zinc`.

**Une échelle nommée.** `text-micro` (10px) et `text-mini` (11px) entrent dans
la configuration Tailwind ; les valeurs en dur disparaissent, `text-[9px]`
compris.

**Un jeu d'icônes.** Le tracé SVG de `NavRail` devient un module `icons.tsx`,
et les 13 fichiers s'y branchent.

## Critères d'acceptation

- [ ] Plus aucune occurrence de `emerald`, `purple`, `orange` ni `yellow`
- [ ] Plus aucune taille de texte en valeur arbitraire (`text-[Npx]`)
- [ ] Plus aucun glyphe ni emoji utilisé comme affordance dans un composant
- [ ] Un test verrouille ces trois règles — l'accrétion revient sinon
- [ ] Les rôles sont documentés là où on les lit, pas dans un fichier à part
- [ ] `npx tsc --noEmit`, `npm run test -- --run`, `npm run build` et les 5
      flows Playwright restent verts
- [ ] Aucun changement de mise en page ni de densité

## Hors scope

- Mode clair
- Refonte de la typographie ou de la grille
