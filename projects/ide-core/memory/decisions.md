# Décisions d'architecture

Ce fichier trace les décisions importantes et leur justification.
Format : ADR léger (Architecture Decision Record).

---

## ADR-001 — Self-hosting comme premier projet

**Date** : 2025-06  
**Décision** : L'IDE se construit lui-même via le projet `ide-core`  
**Raison** : Évite de maintenir deux systèmes séparés. L'IDE mange sa propre cuisine dès le départ, ce qui force à le rendre utilisable rapidement.  
**Alternative rejetée** : Écrire l'IDE "à la main" puis le brancher après.

---

## ADR-002 — Pas de framework agent externe

**Date** : 2025-06  
**Décision** : On implémente notre propre agent loop (pas LangChain, CrewAI, etc.)  
**Raison** : Ces frameworks changent d'API tous les 6 mois. On veut contrôler le protocole de communication entre agents (JSON-RPC), la gestion des tickets, et la mémoire.  
**Alternative rejetée** : LangGraph (trop couplé à l'écosystème LangChain).

---

## ADR-003 — Tickets comme fichiers Markdown

**Date** : 2025-06  
**Décision** : Les tickets sont des fichiers `.md` avec frontmatter YAML, pas une DB  
**Raison** : Lisibles sans l'IDE, versionnables avec git, diffables. La DB vient en couche de cache au-dessus, pas comme source de vérité.  
**Alternative rejetée** : SQLite comme source de vérité pour les tickets.

---

## ADR-004 — Tauri plutôt qu'Electron

**Date** : 2025-06  
**Décision** : Shell desktop en Tauri v2  
**Raison** : Bundle 10x plus léger, accès filesystem natif sécurisé, Rust pour les parties critiques. Microsoft lui-même cherche à sortir d'Electron sur VS Code.  
**Alternative rejetée** : Electron (trop lourd), app web pure (pas d'accès filesystem).

---

## ADR-005 — uv comme gestionnaire Python

**Date** : 2025-06  
**Décision** : `uv` pour toute la gestion des dépendances Python  
**Raison** : 10-100x plus rapide que pip, résolution de dépendances déterministe, remplace pip + venv + poetry en un seul outil.  
**Alternative rejetée** : Poetry (lent), pip (pas de lock file natif).

---

## ADR-006 — ProjectLoader filtre sur CLAUDE.md

**Date** : 2026-06  
**Décision** : `ProjectLoader.list_projects()` ne liste que les dossiers contenant un `CLAUDE.md`, tandis que `list_projects()` (module-level) liste tous les dossiers.  
**Raison** : L'orchestrateur ne doit travailler que sur des projets structurés. La fonction module-level reste disponible comme utilitaire bas niveau pour les tests et scripts.  
**Alternative rejetée** : Filtrer aussi dans la fonction module-level (casserait les tests existants sans apport réel).

---

## ADR-007 — Modèle de projet : `name` parsé depuis le H1 du CLAUDE.md

**Date** : 2026-06  
**Décision** : Le champ `name` d'un `Project` est extrait de la première ligne `# Titre` du CLAUDE.md, avec fallback sur le nom du dossier.  
**Raison** : Le nom du dossier est un identifiant technique (`ide-core`) ; le titre H1 est le nom lisible (`CLAUDE.md — projet ide-core`). Les deux coexistent.  
**Alternative rejetée** : Utiliser uniquement le nom du dossier comme `name` (perd l'intention du CLAUDE.md).

---

## ADR-008 — Orchestrateur sans état interne (stateless)

**Date** : 2026-06  
**Décision** : `Orchestrator` est instancié à chaque requête HTTP (pas de singleton). Il reçoit `AgentRunner`, `TicketService` et `project_context` en injection de dépendances.  
**Raison** : Deux pipelines sur des projets différents peuvent tourner en parallèle sans partage d'état. La concurrence est naturelle car `asyncio` + instances séparées = zéro lock à gérer.  
**Alternative rejetée** : Singleton avec un dictionnaire de verrous par ticket — trop complexe pour la v0.

---

## ADR-009 — Verdict reviewer parsé par mot-clé structuré

**Date** : 2026-06  
**Décision** : L'orchestrateur parse la sortie du reviewer en cherchant `CHANGES_REQUESTED` (prioritaire) puis `APPROVED`. Absence des deux = rejet.  
**Raison** : Le reviewer est prompté pour répondre dans ce format. La priorité de `CHANGES_REQUESTED` évite les faux positifs si les deux mots apparaissent ("sinon APPROVED").  
**Alternative rejetée** : Parser un JSON structuré — trop contraignant pour un LLM qui génère aussi du texte libre.

---

## ADR-010 — github-sync intégré dans POST /agents/run (pas d'endpoint dédié)

**Date** : 2026-06  
**Décision** : `role: github-sync` est géré dans `POST /api/v1/agents/run` avec court-circuit avant le lookup ticket. Retourne un `AgentResult` synthétique.  
**Raison** : Cohérence du contrat API — un seul endpoint pour tous les rôles. `AgentResult.created_tickets` porte déjà le payload utile. `ticket_id` est rendu optionnel (default `""`) pour accommoder les rôles sans ticket cible.  
**Alternative rejetée** : Endpoint dédié `/agents/github-sync` — fragmentation de l'API sans bénéfice pour la v0.

---

## ADR-012 — Monaco bundlé localement (pas CDN)

**Date** : 2026-06-20
**Décision** : Monaco Editor chargé depuis le package npm `monaco-editor`, bundlé via Vite. Pas de CDN jsdelivr.
**Raison** : Les builds Tauri packagés n'ont pas d'accès internet (app distribuée offline). Le CDN fonctionnerait en dev mais casserait en production desktop.
**Alternative rejetée** : CDN uniquement (acceptable en web, inutilisable en desktop packagé).

---

## ADR-013 — Hooks React sans gestionnaire d'état global

**Date** : 2026-06-20
**Décision** : Pas de Zustand/Jotai pour la v0. L'état partagé (projet actif, ticket actif) tient dans `useActiveProject`. Les autres hooks sont autonomes.
**Raison** : Le graphe d'état de la v0 est simple — 2 entités partagées. Ajouter un store serait du surengineering prématuré.
**Alternative rejetée** : Zustand (à réévaluer si on dépasse 5 états globaux partagés entre composants non-parents).

---

## ADR-014 — Vitest + React Testing Library pour les tests frontend

**Date** : 2026-06-20
**Décision** : Vitest pour l'exécution + RTL pour les assertions composants.
**Raison** : Vitest partage la config Vite (transforms, aliases, ESM) sans configuration séparée. RTL encourage les tests par comportement utilisateur, pas par implémentation.
**Alternative rejetée** : Jest (configuration babel séparée, pas d'ESM natif, overhead de setup).

---

## ADR-015 — CI : 3 jobs parallèles GitHub Actions

**Date** : 2026-06-20
**Décision** : `backend` (ubuntu, pytest), `frontend` (ubuntu, tsc+vitest), `tauri` (macos, cargo check) en parallèle.
**Raison** : Séparation des responsabilités + exécution parallèle = feedback rapide. `macos-latest` pour Tauri (headers WKWebView disponibles). `cargo check` et non `cargo build` pour éviter 10+ min de compilation complète.
**Alternative rejetée** : Job unique séquentiel (lent), `cargo build` complet en CI (coûteux).

---

## ADR-016 — Scope filesystem Tauri : $HOME pour la v0

**Date** : 2026-06-20
**Décision** : Le plugin `tauri-plugin-fs` a accès à `$HOME/**` en v0.
**Raison** : Les projets vibe-ide seront dans `~/` (dossier utilisateur). Scope plus restrictif nécessiterait de connaître le chemin exact au build time.
**Alternative rejetée** : Scope filesystem complet `/` (trop large, rejeté par App Store), scope fixe `~/vibe-ide-workspace/` (impose un emplacement).

---

## ADR-011 — httpx natif plutôt que PyGitHub pour l'API GitHub

**Date** : 2026-06  
**Décision** : `GitHubService` utilise `httpx` async directement (déjà dépendance du projet).  
**Raison** : PyGitHub est synchrone et ajoute une abstraction lourde. On n'utilise que 3 endpoints (list issues, add label, remove label). httpx + respx donne des mocks propres en tests.  
**Alternative rejetée** : PyGitHub (blocking I/O), gidgethub (trop orienté webhooks).
