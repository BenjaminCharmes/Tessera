---
id: ticket-118
title: "Finir la montée des dépendances frontend"
type: chore
status: done
pr_number: 137
priority: medium
agent: codeur
depends_on: ["ticket-117"]
estimated_days: 1
created: 2026-09-22
---

# ticket-118 — Finir la montée des dépendances frontend

## Objectif

Traiter ce que la fermeture de la PR Dependabot avait laissé en arrière, et
réduire les vulnérabilités signalées.

## Contexte

La PR #121 portait 26 paquets en bloc. Elle a été fermée pour Tailwind, mais
les vingt-cinq autres restaient à faire — dont TypeScript 7 et Vitest 5.

`npm audit` signalait par ailleurs **9 vulnérabilités** (6 moyennes, 3
élevées), dont quatre sur des dépendances directes.

## Ce qui a été fait

Par paliers vérifiés, jamais en bloc : chaque montée suivie de `tsc` et des
tests, pour que la cause d'une casse soit immédiate.

| Paquet | Vers | Note |
|---|---|---|
| `vitest`, `@vitest/coverage-v8` | 5 | a exigé `jest-dom` 7 |
| `@testing-library/jest-dom` | 7 | l'import passe par `/vitest` |
| `marked` | 18 | quatre majeures d'un coup, sans casse |
| `monaco-editor` | 0.56 | a exigé de réécrire les imports de workers |
| `dompurify`, `vite`, `react`, `eslint`, Playwright… | dernières | mineures |

Les vulnérabilités passent de **9 à 5**. Les cinq restantes sont toutes
**transitives** — `brace-expansion`, `browserslist`,
`baseline-browser-mapping`, et le `dompurify` embarqué par Monaco. Les
corriger demanderait `npm audit fix --force`, donc des ruptures non
souhaitées ; elles se règleront quand les mainteneurs amont monteront.

## Ce que ça ne fait pas : TypeScript 7

**Écarté, et ce n'est pas un renoncement.** `typescript-eslint@8.70.1`, la
dernière version, déclare `peer typescript@">=4.8.4 <6.1.0"` : l'écosystème
ESLint ne supporte pas encore TS 7. Monter quand même aurait cassé le lint ou
forcé un `--legacy-peer-deps` qui masque le conflit sans le résoudre.

Le projet reste en TypeScript 6 jusqu'à ce que `typescript-eslint` suive.

## Deux ruptures trouvées, et par quoi

- **Monaco 0.56** a changé son export map : `"./*": "./esm/vs/*.js"`. Les
  imports de workers perdent leur préfixe `esm/vs/`. Les tests unitaires n'ont
  rien vu — ils mockent Monaco — seul l'**E2E** l'a attrapé, et seulement
  après avoir tué un serveur Vite qui servait encore l'ancien code.
- **Playwright 1.63** réclame un binaire de navigateur plus récent. La CI
  l'installe à chaque run (`npx playwright install --with-deps chromium`),
  donc elle n'est pas concernée ; seul le poste local devait rattraper.

## Critères d'acceptation

- [x] Les paquets directs vulnérables sont montés
- [x] `npm audit` ne signale plus que des vulnérabilités transitives
- [x] `npm run build` passe
- [x] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Dépendances

ticket-117, qui a traité Tailwind à part.

## Estimation

1 jour.

## Risques

Les cinq vulnérabilités restantes demeurent jusqu'à une montée amont. Aucune
n'est exploitable depuis l'interface : ce sont des dépendances d'outillage de
build, et le `dompurify` de Monaco n'est pas celui qui assainit le Markdown
rendu — celui-là est monté.
