---
name: mise-en-ligne
description: Use when a project is served online to the public (site, web app with a public URL) and you build, review or prepare its launch — not for a local-only tool.
---

# Mise en ligne

Un projet servi en ligne oublie toujours les mêmes choses. Cette liste en
compte vingt, avec la façon de les faire **sans dépendance lourde** et qui les
vérifie. Un outil local (lancé sur la machine de son auteur) n'a pas besoin de
tout ça : ne l'applique pas.

Deux colonnes de méthode : **Vite + React 19** (SPA ou pré-rendu) et
**Next.js** (App Router). « machine » = la spec Playwright du §4 peut le
vérifier ; « humain » = un relecteur doit le juger.

## 1. Les vingt points

| # | Point | Vite + React 19 | Next.js | Vérifie |
|---|-------|-----------------|---------|---------|
| 1 | Page 404 | Route `*` qui rend une vraie page ; le serveur statique renvoie le statut 404 (`404.html` ou règle de repli) | `app/not-found.tsx` | machine |
| 2 | CTA visible sans défiler | Le bouton d'action principal est dans le premier écran à 1280×720 et à 375×667 | idem | machine |
| 3 | `<title>` par page | `<title>` rendu dans le composant de la page : React 19 le hisse dans `<head>` | `metadata` / `generateMetadata` | machine |
| 4 | Meta description par page | `<meta name="description">` dans le composant de la page, 70 à 160 caractères | `metadata.description` | machine |
| 5 | Image Open Graph | `<meta property="og:image">` vers une URL absolue, image 1200×630 servie en 200 | `opengraph-image.tsx` ou `metadata.openGraph` | machine |
| 6 | Favicons | `favicon.svg` + `apple-touch-icon.png` (180 px) liés dans `index.html` | `app/icon.*` et `app/apple-icon.*` | machine |
| 7 | `robots.txt` | `public/robots.txt`, avec la ligne `Sitemap:` | `app/robots.ts` | machine |
| 8 | `sitemap.xml` | `public/sitemap.xml` à jour, ou généré au build depuis la liste des routes | `app/sitemap.ts` | machine |
| 9 | `alt` sur chaque image | `alt` descriptif ; `alt=""` si l'image est décorative | idem (`next/image` l'exige) | machine |
| 10 | Points de rupture mobile | Mise en page contrôlée à 375, 768 et 1280 px, sans défilement horizontal | idem | humain |
| 11 | CTA collant sur mobile | Barre d'action `position: sticky` / `fixed` en bas sous le point de rupture, sans masquer le contenu | idem | humain |
| 12 | États de chargement | Un état visible pour chaque donnée ou envoi asynchrone (squelette, bouton désactivé) | `loading.tsx`, `Suspense` | humain |
| 13 | États d'erreur des formulaires | Message par champ, lié par `aria-describedby`, plus un message d'échec d'envoi | idem | humain |
| 14 | Page de remerciement | Route dédiée après envoi (et non un simple message qui disparaît) | idem | machine |
| 15 | Politique de confidentialité | Page liée dans le pied de page, texte issu du gabarit du §4 | idem | humain |
| 16 | CGU | Seulement avec des comptes ou des ventes ; sinon n'en crée pas | idem | humain |
| 17 | Bandeau cookies | Selon la règle du §2 | idem | machine |
| 18 | Mesure d'audience | Un script exempté de consentement (voir §2), chargé en `defer` | `next/script`, `strategy="afterInteractive"` | machine |
| 19 | Vraie adresse de contact | Une adresse qui existe et qu'on lit ; jamais `contact@example.com` ni `À_REMPLACER` | idem | humain |
| 20 | Mentions légales | Page liée dans le pied de page (LCEN, obligatoires en France), texte issu du gabarit du §4 | idem | humain |

## 2. Bandeau cookies et mesure d'audience

**Une mesure d'audience exemptée de consentement, sans autre traceur, dispense
du bandeau cookies.** Sont exemptés : Plausible, Umami, GoatCounter, et Matomo
configuré pour l'exemption CNIL. Dans ce cas :

- ne pose **pas** de bandeau, et dis-le dans la page de confidentialité ;
- ne charge aucun autre traceur (pixel publicitaire, vidéo intégrée avec
  cookies, widget social) : un seul suffit à rétablir le bandeau.

Sinon (Google Analytics, pixel, intégration tierce qui dépose un cookie), le
consentement est préalable : utilise **`vanilla-cookieconsent`**, sans
dépendance, et ne charge le script tiers qu'après l'acceptation. Aucun
développement maison de bandeau.

## 3. Métadonnées : pas de bibliothèque en plus

**N'ajoute pas `react-helmet-async`.** React 19 rend `<title>`, `<meta>` et
`<link>` écrits dans un composant et les place dans `<head>` : un composant de
page suffit.

```tsx
function Accueil() {
  return (
    <>
      <title>Nom du site — accroche courte</title>
      <meta name="description" content="Une phrase qui donne envie de cliquer." />
      <meta property="og:image" content="https://exemple.fr/og.png" />
      {/* contenu de la page */}
    </>
  )
}
```

Next.js n'a pas besoin de ça non plus : `metadata`, `sitemap.ts`, `robots.ts`,
`opengraph-image` et `not-found.tsx` couvrent les points 1, 3 à 5, 7 et 8.

## 4. Textes juridiques

Les textes juridiques sont des **gabarits relus par un humain**. Tu ne les
rédiges jamais comme définitifs. Toute valeur que tu ne connais pas porte le
marqueur `À_REMPLACER` ; tu ne l'inventes pas et tu ne la devines pas.

```markdown
# Mentions légales

> Gabarit à relire par un humain avant publication.

**Éditeur** : À_REMPLACER (nom ou raison sociale)
**Statut** : À_REMPLACER (particulier, micro-entreprise, société)
**Adresse** : À_REMPLACER
**Contact** : À_REMPLACER (adresse e-mail qui existe)
**Directeur de la publication** : À_REMPLACER
**Hébergeur** : À_REMPLACER (nom, adresse, téléphone)
```

Pour la politique de confidentialité, le gabarit suit la même forme : données
collectées, finalité, durée de conservation, droits d'accès et de
suppression, contact — chaque valeur inconnue en `À_REMPLACER`.

**Tant qu'un `À_REMPLACER` reste dans le dépôt, signale-le dans ton rapport
comme bloquant pour la mise en ligne** : n'écris pas « terminé ». Il se
cherche d'une commande : `grep -r "À_REMPLACER" src public`.

## 5. Le contrôle

Une spec Playwright (`e2e/mise-en-ligne.spec.ts`) couvre ce que la machine
peut juger :

- une URL inconnue répond **404** et affiche la page 404 ;
- `/robots.txt` et `/sitemap.xml` répondent **200** ;
- l'URL de `og:image` répond **200** ;
- le CTA principal est visible à **375 px**, sans défiler ;
- **aucune requête vers un traceur** avant consentement (écoute de
  `page.on('request')` sur les domaines tiers connus).

Cette spec porte les points 1, 2, 5, 7, 8 et 17. Les autres restent à la
relecture humaine : dis lesquels dans ton rapport.

**Mets le build dans le `test_command` du projet** (`npm --prefix frontend run
build`, ou `next build`) : une erreur qui ne casse qu'au build — bundler, typage
du framework, asset invalide — traverse sinon tous les contrôles et ne se voit
qu'en CI. Tessera avertit dans `pipeline-log.md` quand il manque.

**Lighthouse CI** ne se met en place qu'**après un premier déploiement**, et
contre l'URL réelle : contre un serveur local, ses scores ne disent rien de
la production.

## 6. Pour aller plus loin

Pour un audit approfondi (performance, accessibilité, bonnes pratiques),
`addyosmani/web-quality-skills` (licence MIT) sert de référence. C'est une
lecture, pas une dépendance : n'ajoute rien au projet pour l'utiliser.
