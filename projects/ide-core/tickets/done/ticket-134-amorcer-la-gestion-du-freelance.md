---
id: ticket-134
title: "Amorcer un projet de gestion de l'activité freelance"
type: design
status: done
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-134 — Amorcer un projet de gestion de l'activité freelance

## Objectif

Décider ce qu'un projet « freelance » contient avant d'en écrire la première
ligne : suivi de l'activité, et éventuellement aide à la prospection.

## Contexte

Le besoin énoncé tient en deux morceaux qui n'ont ni le même risque ni la même
difficulté :

- **gérer** — missions, clients, temps, facturation, échéances. Des données,
  des vues, rien d'inhabituel ;
- **automatiser la prospection** — c'est là que ça se corse. Contacter des
  prospects par un moyen automatisé engage une réputation professionnelle, et
  l'envoi de messages non sollicités est encadré. Un agent qui écrit à des
  inconnus au nom de quelqu'un est une décision, pas une fonctionnalité.

À relier au projet `carriere`, qui documente déjà une clause d'exclusivité
exigeant une autorisation préalable et expresse de l'employeur pour l'activité
freelance. Les deux projets parlent du même sujet par deux bouts.

## Solution proposée

Séparer franchement les deux volets et ne cadrer que le premier dans ce
ticket :

1. **Gestion** — quelles entités (mission, client, facture, échéance), quelle
   persistance, quelles vues. Accessible depuis plusieurs postes, donc même
   question d'hébergement que ticket-133.
2. **Prospection** — **tranché : l'agent prépare, et rien de plus.** Il
   constitue des listes et documente les cibles ; la rédaction et l'envoi
   restent à la main. C'est la forme d'ADR-022 appliquée ici : le point où un
   humain tranche est ce qui rend acceptable tout le reste de
   l'automatisation.

## Critères d'acceptation

- [ ] Les entités du volet gestion sont listées, avec leurs relations
- [ ] La décision dit où vivent les données et ce qui part sur GitHub privé
- [ ] La décision rappelle que l'agent prépare seulement, et que ni la
      rédaction ni l'envoi ne lui reviennent
- [ ] Le lien avec la clause d'exclusivité documentée dans `carriere` est
      tranché : ce projet suppose-t-il l'autorisation obtenue ?
- [ ] Les tickets d'implémentation sont créés dans le projet concerné

## Dépendances

Aucune. Gagne à être fait après ticket-133, qui tranche les mêmes questions
d'hébergement et de confidentialité.

## Estimation

1 jour.

## Risques

Un agent qui envoie des messages à des tiers au nom de quelqu'un engage cette
personne. Le défaut doit être « l'agent prépare, l'humain envoie » — sur le
modèle d'ADR-022 pour le merge : le point où un humain tranche est ce qui rend
acceptable tout le reste de l'automatisation.

---

## Décision — 2026-09-23

### Le lien avec la clause d'exclusivité — tranché en premier

`projects/carriere/analyses/00-urgent-clause-exclusivite.md` existe, et le
projet contient déjà un modèle de `demande-autorisation-activite-exterieure`.

**Ce projet ne suppose pas l'autorisation obtenue.** Je n'ai aucun moyen de
savoir où en est cette démarche, et supposer que oui serait supposer le point
le plus lourd du dossier.

La conséquence est concrète, pas cosmétique : le projet est un outil de
**suivi**, il n'est pas un outil d'exercice. Suivre une activité, la chiffrer,
préparer des documents ne requiert aucune autorisation. Démarcher un client en
requiert une. C'est exactement la frontière tracée ci-dessous, et elle se
trouve coïncider avec celle qu'imposait déjà le risque de la prospection.

Le premier ticket du projet portera cette question et rien d'autre : l'état de
l'autorisation, et ce qu'il permet.

### 1. Les entités du volet gestion

```
Client 1──n Mission 1──n Prestation
                │            │
                │            └── (date, durée, description)
                │
                └──n Facture 1──n Ligne
                          │
                          └── Échéance (date, état)
```

- **Client** — nom, contact, conditions de paiement convenues
- **Mission** — un engagement chez un client : période, taux, statut
- **Prestation** — une unité de temps travaillé, rattachée à une mission
- **Facture** — émise pour une mission, composée de lignes
- **Échéance** — ce qui rend une facture en retard ou non

La relation qui compte est `Prestation → Facture` : c'est elle qui dit ce qui
est fait mais pas encore facturé, et c'est la question qu'on pose le plus
souvent à un tel outil.

### 2. Où vivent les données, et ce qui part sur GitHub

Même régime que ticket-133, pour la même raison.

- **Le code** part sur un GitHub privé.
- **Les données** — clients, montants, factures — **restent sur la machine**.
  Des noms de clients et des montants facturés identifient une activité
  professionnelle ; combinés à la clause d'exclusivité ci-dessus, ce sont les
  deux moitiés d'un même problème.

En pratique : SQLite local, exclu par `.git/info/exclude` et non par
`.gitignore` (ADR-021), et le mode d'artefacts en `local` (ADR-023).

### 3. La prospection — l'agent prépare, et rien de plus

Confirmé, et c'est une contrainte, pas un défaut de version 0.

L'agent constitue des listes, documente des cibles, rassemble du contexte. La
**rédaction** et l'**envoi** restent à la main, intégralement. C'est la forme
d'ADR-022 appliquée ici : le point où un humain tranche est ce qui rend
acceptable tout le reste de l'automatisation.

La raison n'est pas seulement réglementaire. Un message envoyé à un inconnu au
nom de quelqu'un engage la réputation de cette personne, dans un métier où
elle est le principal actif. Une erreur de merge se révoque ; un message envoyé
ne se reprend pas.

### Ordonnancement

Ce projet vient **après** `carriere-app` (ticket-133). Les deux posent les
mêmes questions d'hébergement et de confidentialité, et les résoudre une fois
sur le projet le moins engageant évite de les rejouer ici.
