---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 0.5
id: ticket-447
pr_number: null
priority: medium
status: done
title: A mise-en-ligne skill gives agents the launch checklist of a project served
  online
type: feat
---

# ticket-447 — Skill `mise-en-ligne` pour les projets servis en ligne

## Objectif

Les agents d'un projet servi en ligne disposent d'une liste de contrôle de
mise en ligne, avec la façon de faire chaque point sans dépendance lourde.

## Contexte

Benjamin a listé le 15/10 dix-neuf points qu'on oublie au lancement : page
404, CTA visible sans défiler, title et meta description par page, image
Open Graph, favicons, robots.txt, sitemap.xml, alt sur chaque image, points
de rupture mobile, CTA collant sur mobile, états de chargement, états
d'erreur des formulaires, page de remerciement, politique de
confidentialité, CGU, bandeau cookies, mesure d'audience, vraie adresse de
contact. Un audit du même jour y ajoute les **mentions légales** (LCEN,
obligatoires en France) et conclut :

- une mesure d'audience exemptée de consentement (Plausible, Umami,
  GoatCounter, Matomo configuré pour l'exemption CNIL) sans autre traceur
  dispense du bandeau cookies ; sinon `vanilla-cookieconsent`, sans
  dépendance ;
- React 19 rend `<title>` et `<meta>` nativement : pas de
  `react-helmet-async` ; Next.js couvre `metadata`, `sitemap.ts`,
  `robots.ts`, `opengraph-image` et `not-found.tsx` ;
- les CGU ne servent qu'avec des comptes ou des ventes ;
- les textes juridiques sont des gabarits relus par un humain, jamais
  rédigés comme définitifs par un agent.

Pronosti (make-your-call) a déjà appliqué la liste à la main ; le skill la
rend disponible à tout projet qui le déclare.

Les skills du produit vivent dans `agents/plugin/skills/<nom>/SKILL.md`,
sur le modèle de `agents/plugin/skills/design-ui/SKILL.md`, et se déclarent
par rôle dans `agents.json` (`"skills": ["tessera:<nom>"]`).

## Solution proposée

Créer `agents/plugin/skills/mise-en-ligne/SKILL.md` (moins de 200 lignes),
en français :

1. Frontmatter `name: mise-en-ligne` et une `description` qui commence par
   « Use when » et vise un projet servi en ligne (pas un outil local).
2. Un tableau des vingt points : le point, la façon de le faire en Vite +
   React 19 et en Next.js, et qui le vérifie (« machine » ou « humain »).
3. La règle du bandeau cookies ci-dessus.
4. Les textes juridiques : gabarit à valeurs factices marquées
   `À_REMPLACER`, que l'agent signale comme bloquantes au lieu de les
   remplir.
5. Le contrôle : une spec Playwright couvrant 404 (statut et page),
   robots.txt et sitemap.xml en 200, og:image en 200, CTA visible à 375 px,
   aucune requête vers un traceur avant consentement ; Lighthouse CI
   seulement après un premier déploiement, contre l'URL réelle.
6. Pour un audit approfondi, renvoyer à `addyosmani/web-quality-skills`
   (MIT) comme référence, sans en faire une dépendance.

Le branchement dans les `agents.json` des projets en ligne (portfolio,
make-your-call, curio) se fait à la main après le merge : `agents.json` est
hors d'atteinte des agents.

## Critères d'acceptation

- [ ] `agents/plugin/skills/mise-en-ligne/SKILL.md` existe, avec un
      frontmatter `name: mise-en-ligne` et une `description` commençant par
      « Use when »
- [ ] Le skill liste les vingt points, mentions légales comprises
- [ ] Le skill dit qu'une mesure d'audience exemptée de consentement, sans
      autre traceur, dispense du bandeau cookies
- [ ] Le skill interdit `react-helmet-async` et cite les métadonnées
      natives de React 19
- [ ] Le skill demande des gabarits juridiques marqués `À_REMPLACER`
- [ ] Un test de `backend/tests/` vérifie que
      `agents/plugin/skills/mise-en-ligne/SKILL.md` existe et que son
      frontmatter porte `name: mise-en-ligne`

## Ce que ça ne fait pas

- Ne modifie aucun `agents.json` (fait à la main ensuite).
- N'installe aucun outil : ni Lighthouse CI, ni Playwright dans un projet.