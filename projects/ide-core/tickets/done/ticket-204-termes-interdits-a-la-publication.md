---
agent: architect
created: 2026-09-28
depends_on: []
estimated_days: 1
id: ticket-204
pr_number: null
priority: high
status: done
title: Refuser de publier un terme interdit, sur tous les projets
type: design
---

# ticket-204 — Refuser de publier un terme interdit, sur tous les projets

## Objectif

Qu'aucun projet ne pousse vers GitHub un commit dont le contenu, le message
ou les métadonnées contiennent un terme de la liste de l'utilisateur — pour
que la règle d'ADR-043 soit **vérifiée**, pas seulement énoncée.

## Contexte

ADR-043 interdit toute donnée professionnelle dans un dépôt personnel. Deux
contrôles existent, et aucun ne vérifie la publication :

- l'identité git par dossier (`includeIf`) protège l'auteur des commits faits
  à la main, **pas** ceux de l'orchestrateur, qui commite lui-même (ADR-018) ;
- les hooks git ne servent pas de filet : `GitWorkspaceService` force
  `core.hooksPath` vers un dossier vide (ADR-027), donc un hook global ne
  tournerait pas sur les commits de Tessera.

Le portfolio a déjà son propre filet au build (`FORBIDDEN_TERMS`, sa PR #1).
Il protège le site, pas les autres dépôts.

## Solution proposée (à trancher par l'architect)

1. **Une liste par machine, jamais versionnée** : `FORBIDDEN_TERMS` dans le
   `.env` du backend (déjà ignoré), même format que celui du portfolio —
   termes séparés par des virgules, correspondance insensible à la casse, aux
   accents et aux séparateurs, mots entiers. Un domaine d'adresse (par
   exemple `acme-corp.com`) s'y déclare comme un terme.
2. **Le contrôle se fait au push**, pas au commit : un commit local ne publie
   rien, et ADR-018 veut que chaque run se termine par un commit. Avant tout
   push de `GitHubWorkflowService` ou de `LivraisonService` : lignes ajoutées
   du diff par rapport à la base, messages de commit, auteur et committer de
   chaque commit poussé.
3. **Refus fermé** : un terme trouvé bloque le push et arrête la livraison
   avec un `arret` qui nomme les fichiers ou les commits en cause, **jamais le
   terme** (un log se partage). Le run garde son résultat (ADR-030).
4. **Exemption déclarée** : un dépôt de travail contient légitimement le nom
   de son client. Un projet se déclare `"confidentiality": "professional"`
   dans `agents.json` pour sortir du contrôle ; défaut et valeur inconnue :
   contrôlé (forme d'ADR-023 — le défaut protège).
5. **Écrire l'ADR** qui acte le mécanisme (skill `write-adr`).

À trancher : faut-il aussi vérifier le dépôt de Tessera lui-même lors des
commits faits hors de l'IDE (pre-push versionné, qui lit la même liste) ?

## Critères d'acceptation

- [ ] L'ADR est écrit et dit où vit la liste, quand le contrôle s'exécute et
      comment un projet s'en exempte
- [ ] La décision dit ce qui arrive quand la liste est vide ou absente
- [ ] Les tickets d'implémentation sont créés dans `ide-core`, chacun avec des
      critères vérifiables par un test
- [ ] Aucun fichier versionné, test ou exemple ne contient un vrai terme de la
      liste — les exemples sont inventés

## Dépendances

Aucune.

## Estimation

1 jour de cadrage ; l'implémentation est de l'ordre de deux tickets.

## Ce que ça ne fait pas

Le filet attrape un **nom**, pas une **histoire** : une anecdote de travail
sans aucun nom passe. La relecture humaine reste la vraie porte.

## Risques

Un contrôle trop large (sous-chaînes, termes courts) bloque des pushes
légitimes, et un filet qui crie à tort finit désactivé. Mots entiers
uniquement, et un refus qui dit **où** chercher.