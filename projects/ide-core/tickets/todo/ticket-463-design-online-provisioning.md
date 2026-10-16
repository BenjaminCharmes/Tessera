---
id: ticket-463
title: "Design how Tessera provisions a project online (Vercel, Neon, Resend, Stripe, Cloudflare) without exposing its tokens"
type: design
status: todo
pr_number: null
priority: high
agent: architect
depends_on: []
estimated_days: 1
created: 2026-10-16
---

# ticket-463 — Concevoir la mise en ligne d'un projet par Tessera

## Objectif

Fixer, avant tout code, comment Tessera crée et relie lui-même les
ressources en ligne d'un projet, et comment il garde les jetons de ces
services hors de portée des agents et des dépôts.

## Contexte

Demandé par Benjamin le 16/10. Pour mettre Pronosti (make-your-call) en
ligne, il faut aujourd'hui, à la main : créer le projet Vercel relié au
dépôt GitHub, créer la base Neon (désormais via l'intégration Vercel),
déclarer le domaine et une clé dans Resend, créer produit, prix et webhook
dans Stripe, poser les enregistrements DNS, puis recopier chaque secret
dans les variables Vercel. Le même travail reviendra pour chaque projet en
ligne (portfolio, curio, Souhaito…), sur les mêmes comptes partagés.

Les quatre services ont une API. Les jetons donnent un accès large (un
jeton Vercel ouvre tout le compte) : leur garde est le cœur du sujet.
Contraintes en vigueur : un agent n'écrit pas hors de son projet (ADR-031),
ne lance pas de commande git ou gh en écriture (ADR-027), et une porte qui
ne peut pas juger refuse (ADR-039, ADR-050). Le projet `make-your-call`
liste ses variables dans `projects/make-your-call/.env.example`.

## Ce que doit produire l'architecte

1. Un ADR dans `projects/ide-core/memory/decisions.md` (format du skill
   write-adr) qui tranche :
   - **Garde des jetons** : seulement dans le `.env` de Tessera, lus par le
     backend ; jamais transmis à un agent, jamais écrits dans un dépôt, un
     ticket, un journal ni une réponse d'API ; masqués dans les logs.
   - **Qui déclenche** : une action explicite de Benjamin (bouton ou
     endpoint), jamais un agent du pipeline.
   - **Portée minimale** de chaque jeton : clé Stripe restreinte et mode test
     par défaut, jeton Vercel avec expiration, jeton Cloudflare limité à la
     zone DNS.
   - **Idempotence** : relancer la mise en ligne retrouve et complète ce qui
     existe, ne crée pas de doublon.
   - **Ce qui reste humain** : création des comptes, achat du domaine,
     activation du mode réel Stripe.
2. Une section « Mise en ligne » dans `docs/architecture.md` : les étapes,
   l'ordre (projet Vercel → base → variables → domaine Resend + DNS →
   Stripe produit, prix, webhook → redéploiement), ce qui est relu à chaque
   relance, et la déclaration par projet dans `agents.json` (services
   voulus, nom du domaine).
3. Le découpage en tickets d'implémentation, écrits dans
   `projects/ide-core/tickets/todo/` (numéros suivants), chacun avec des
   critères vérifiables et sans dépasser six critères : un ticket par
   service intégré, un pour l'orchestration et la reprise, un pour
   l'endpoint. L'écran (bouton « Mettre en ligne », état par étape) passera
   par une maquette : le ticket d'interface le dit et dépend de l'endpoint.

## Critères d'acceptation

- [ ] `projects/ide-core/memory/decisions.md` contient un nouvel ADR qui
      traite la garde des jetons, le déclenchement, la portée minimale,
      l'idempotence et ce qui reste humain
- [ ] `docs/architecture.md` contient une section « Mise en ligne » qui
      liste les étapes dans l'ordre
- [ ] Au moins quatre tickets d'implémentation existent dans
      `projects/ide-core/tickets/todo/`, chacun avec au plus six critères
- [ ] Aucun jeton, clé ni secret réel n'apparaît dans le diff

## Ce que ça ne fait pas

- N'écrit aucun code, n'appelle aucune API, ne crée aucun compte.
