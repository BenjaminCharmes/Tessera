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

---

## ADR-017 — Abstraction `LLMProvider`, abonnement Claude par défaut

**Date** : 2026-09
**Décision** : Les services passent par un protocole `LLMProvider` (`complete`/`stream`), jamais par le SDK directement. Deux implémentations : `ClaudeAgentSDKProvider` (défaut, abonnement, outils fichier) et `AnthropicApiProvider` (crédits API). `get_provider(allow_tools=False)` sert une variante sans outils aux services purement texte→JSON.
**Raison** : L'abonnement est gratuit à l'usage, la Messages API est facturée au token — l'abonnement est donc le mode quotidien. Le provider API reste nécessaire là où aucune session interactive n'existe (Docker, CI).
**Alternative rejetée** : Un seul provider Messages API (perd l'usage gratuit) ; donner le jeu d'outils complet aux services non-agentiques (surface de dérapage inutile).
**Détail** : voir `tickets/done/ticket-044-agent-sdk-migration.md`. Les invariants (`cwd` résolu, `tools` **et** `allowed_tools` toujours explicites) sont documentés là où ils s'appliquent, dans `services/providers/agent_sdk.py`.

---

## ADR-018 — Une branche et un commit par run de pipeline

**Date** : 2026-09-15
**Décision** : Chaque run s'exécute sur sa propre branche, relit le **diff git réel** plutôt que la prose du codeur, et se termine toujours par un commit — typé du ticket si approuvé, `chore: … — unapproved work (…)` sinon. Seul un run approuvé avance la ref de base.
**Raison** : Depuis ADR-017 les agents écrivent vraiment sur disque ; relire leur prose validait une intention, pas une implémentation. Committer à tous les coups garde l'arbre propre pour le ticket suivant sans perdre le travail rejeté. N'avancer la base que sur approbation donne l'isolation **et** l'empilement d'un plan séquentiel.
**Alternative rejetée** : Laisser l'arbre sale pour inspection (bloque le ticket suivant) ; `wip:` comme préfixe (pas un type Conventional Commits, et ces messages vont dans le dépôt de l'utilisateur).
**Conséquence assumée** : du code bloqué par l'audit sécurité entre dans l'historique git, confiné à la branche du ticket et jamais sur `main`.
**Détail** : voir `tickets/in-progress/ticket-045-pipeline-diff-reel.md`.

---

## ADR-019 — Le chat de l'IDE commite comme un run de pipeline

**Date** : 2026-09-15
**Décision** : Le chat conversationnel (ticket-048) écrit sur une branche `chat/<horodatage>` et commite son travail, exactement comme un run de pipeline le fait sur sa branche de ticket. Il ne laisse jamais l'arbre de travail sale.
**Raison** : ADR-018 fait reposer l'enchaînement des tickets sur un arbre propre au démarrage de chaque run. Un chat qui écrit sans committer enverrait le ticket suivant en `blocked` sans qu'aucun agent n'ait tourné. Traiter le chat comme un producteur de travail de première classe évite d'inventer un second régime d'écriture à côté de celui du pipeline.
**Alternative rejetée** : Limiter le chat aux fichiers hors arbre suivi et proposer un diff (sûr, mais fait du chat un outil de seconde classe) ; poser un verrou qui empêche le pipeline de démarrer (simple, mais sérialise chat et pipeline alors qu'ils travaillent sur des branches distinctes). Une branche `chat/*` de trop se supprime ; un arbre cassé bloque la file.

---

## ADR-020 — Deux plafonds distincts : dépense estimée et quota réel

**Date** : 2026-09-15
**Décision** : Un run autonome s'arrête sur **deux** conditions indépendantes, vérifiées entre deux tickets : la dépense cumulée estimée (`RUN_MAX_BUDGET_USD`, ticket-052) et le quota d'abonnement réel remonté par le fournisseur (`QuotaTracker`, ticket-054). Un quota **inconnu** ne bloque jamais.
**Raison** : Les deux mesurent des choses différentes. La dépense estimée se calcule à partir des tokens et d'une grille tarifaire ; le quota est une fenêtre glissante imposée par le fournisseur, qui peut couper un run alors qu'aucun plafond local n'a bougé. Ne suivre que l'un des deux laisse l'autre panne intacte.
**Alternative rejetée** : Déduire le quota de la dépense estimée (les deux ne sont pas proportionnels) ; traiter l'absence d'événement comme un quota nul (un fournisseur muet deviendrait indiscernable d'un quota épuisé, et l'IDE refuserait de travailler sans raison).
**Invariant** : la vérification se fait **entre** deux tickets, jamais au milieu d'un — s'arrêter en cours de ticket laisserait son travail non commité, ce qu'ADR-018 interdit.
**Détail** : voir `tickets/done/ticket-054-quota-abonnement.md`.
