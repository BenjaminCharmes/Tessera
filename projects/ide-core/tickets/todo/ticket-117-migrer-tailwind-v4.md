---
id: ticket-117
title: "Décider, puis mener la migration vers Tailwind v4"
type: chore
status: todo
pr_number: null
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

Dependabot a proposé un lot de **26 paquets frontend** en une PR. Trois
entrées n'y sont pas des mises à jour :

| Paquet | Avant | Après |
|---|---|---|
| `tailwindcss` | `^3.4.19` | **`^4.3.3`** |
| `typescript` | `~6.0.2` | `~7.0.2` |
| `vitest` | `^4.1.9` | `^5.0.1` |

Tailwind v4 change le modèle de configuration : la configuration passe dans le
CSS, `tailwind.config.js` disparaît, le moteur est réécrit. Or `CLAUDE.md`
déclare **« Tailwind CSS v3 »** dans la stack du projet.

La PR a donc été **fermée**, pas mergée. Trois raisons :

1. Elle changerait la stack déclarée sans ticket ni ADR.
2. Vingt-six paquets en un commit rendent la bissection impossible si quelque
   chose casse.
3. **La CI ne protège pas sur l'essentiel.** Une régression Tailwind est
   visuelle : `tsc`, Vitest et Playwright peuvent rester verts pendant que la
   mise en page est cassée. ADR-026 fixe la palette et les tailles nommées,
   et rien ne mesure le rendu.

## Solution proposée

Ce ticket est d'abord une **décision**, pas une exécution. Dans l'ordre :

1. Lire le guide de migration officiel et recenser ce que v4 casse ici :
   `tailwind.config.js`, les tailles de texte nommées d'ADR-026, la couche
   `@layer` utilisée dans `index.css`.
2. Décider si la migration vaut son coût. Rester en v3 est une réponse
   valable — v3 reste maintenue, et la stack marche.
3. Si oui : migrer **seule**, sans les vingt-cinq autres paquets, avec une
   relecture visuelle écran par écran. Mettre à jour `CLAUDE.md` — ce qui
   demande son propre ticket (règle 5).

TypeScript 7 et Vitest 5 se traitent séparément, chacun dans son ticket : ils
n'ont rien à voir avec Tailwind et leur CI, elle, est probante.

## Critères d'acceptation

- [ ] Le coût et le bénéfice de la migration sont écrits, et la décision est
      prise — y compris si elle est de rester en v3
- [ ] Si migration : `npm run build` passe, et chaque écran a été relu
- [ ] Si migration : `CLAUDE.md` ne déclare plus une version fausse
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

Ne bloque pas les autres mises à jour. Dependabot reproposera les paquets
mineurs au prochain cycle ; seul le lot contenant Tailwind est écarté.

## Dépendances

Aucune.

## Estimation

3 jours, dont l'essentiel en relecture visuelle.

## Risques

Le vrai risque n'est pas technique mais silencieux : une migration qui passe
tous les tests et dégrade le rendu. C'est pourquoi la relecture écran par
écran fait partie des critères, et non le seul verdict de la CI.
