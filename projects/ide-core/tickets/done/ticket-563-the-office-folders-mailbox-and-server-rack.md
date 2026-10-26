---
agent: codeur
created: 2026-10-23
depends_on:
- ticket-560
- ticket-562
estimated_days: 1.5
id: ticket-563
plan: true
pr_number: 640
priority: medium
status: done
title: The office folders, mailbox and server rack
type: feat
---

# ticket-563 — Dossiers, boîte aux lettres et baie de serveur

## Objectif
Ajouter à la pièce trois objets qui montrent chacun un état réel : la pile de
dossiers (tickets restants), la boîte aux lettres (PR) et la baie (services).

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md`,
lignes « Pile de dossiers », « Boîte aux lettres », « Baie de serveur ».
Maquettes : `design/maquette/Bureau.dc.html` et
`design/maquette/Bureau-Compact.dc.html` (colonnes « dossiers », « courrier »,
« services »). `restants` d'un run vivant est juste depuis le ticket-560.

## Solution proposée
- `Dossiers.tsx` : le nombre de dossiers = `restants` de `GET /runs/{id}`,
  relu à chaque `queue_progress` et toutes les 30 s tant que le run vit.
  Aucune pile quand `restants` est vide.
- `BoiteAuxLettres.tsx` : lit `boiteAuxLettres` (ticket-561) ; le numéro de PR
  est lié à l'URL de la PR. Après un rechargement de page, l'état se relit par
  `GET /projects/{id}/pr-statuses`.
- `BaieDeServeurs.tsx` : `GET /projects/{id}/services` et le type
  `ServiceActif`, avec `service_output` et `service_closed` pour l'état. Les
  boutons lancer et arrêter reprennent les composants de `ServicesLances`, sans
  les recopier. Rien de déclaré : pas de baie (ADR-042).

## Critères d'acceptation
- [ ] La pile affiche autant de dossiers que `restants` en contient, et rien quand `restants` est vide, et un test le vérifie
- [ ] Un `queue_progress` déclenche une relecture de `GET /runs/{id}`, et un test le vérifie avec un client simulé
- [ ] La boîte aux lettres rend cinq états distincts (aucune, ouverte, CI en attente, mergée, refusée), chacun avec un `aria-label` différent, et un test le vérifie
- [ ] Après un rechargement, l'état de la boîte se relit par `GET /projects/{id}/pr-statuses`, et un test le vérifie
- [ ] La baie n'est pas rendue pour un projet sans service déclaré, et un test le vérifie
- [ ] Lancer ou arrêter un service depuis la baie appelle les mêmes endpoints que `ServicesLances`, et un test le vérifie
- [ ] Aucun fichier du diff ne dépasse 300 lignes, et le diff ne modifie aucun fichier de `backend/`
- [ ] `npm run test`, `tsc` et `eslint` passent

## Ce que ça ne fait pas
- Aucun événement nouveau : l'état « CI en attente » se déduit de `livraison_done` et `ci_merge_done`.
- Ne montre pas la sortie des services : elle reste dans `ServicesLances`.
- Ne remplace pas la vue par défaut (ticket-567).