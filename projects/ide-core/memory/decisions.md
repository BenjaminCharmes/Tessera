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

---

## ADR-021 — Les artefacts vibe-ide s'excluent par `.git/info/exclude`, jamais par `.gitignore`

**Date** : 2026-09-15
**Décision** : Un projet déclare dans `agents.json` si ses `tickets/`, `memory/`, `CLAUDE.md` et `agents.json` partent dans son dépôt (`tracked`) ou restent sur la machine (`local`). En mode `local`, l'exclusion est écrite dans `.git/info/exclude`, entre marqueurs, et **jamais** dans `.gitignore`. Défaut : `tracked` pour un projet créé ou importé, `local` pour un projet cloné.
**Raison** : `.gitignore` est lui-même versionné. Le modifier sur un dépôt client produit un diff visible qui annonce exactement ce qu'on voulait garder hors du dépôt. `.git/info/exclude` a la même sémantique, reste local au clone et n'apparaît ni dans l'historique ni dans un diff. Le défaut diffère selon l'origine parce qu'un dépôt cloné appartient déjà à quelqu'un d'autre : on peut toujours choisir de partager ensuite, on ne peut pas défaire un push.
**Alternative rejetée** : Un réglage global (le bon choix dépend du projet, pas de la machine) ; `.gitignore` (versionné, donc contre-productif) ; retirer automatiquement de l'index les artefacts déjà suivis (`git rm --cached` modifie l'historique à venir du dépôt de l'utilisateur : ça se propose, ça ne se fait pas en silence).
**Détail** : voir `tickets/done/ticket-062-artefacts-locaux-ou-versionnes.md`.

---

## ADR-022 — L'agent de workflow pousse et ouvre la PR, il ne merge jamais

**Date** : 2026-09-15
**Décision** : `GitHubWorkflowService` pousse la branche du ticket puis ouvre sa PR. Aucune méthode publique, aucun appel, ne merge — deux tests le verrouillent, dont un qui inspecte le code source du module.
**Raison** : merger, c'est décider qu'un travail est bon. C'est le seul point du pipeline où un humain tranche, et c'est précisément ce qui rend acceptable tout le reste de l'automatisation : un agent qui mergerait rendrait la relecture facultative.
**Corollaire** : le push n'est **jamais** forcé. Cette branche part dans le dépôt de l'utilisateur, parfois celui d'un client ; écraser une référence distante peut détruire du travail qui n'est pas le nôtre. Un push refusé est une décision à remonter, pas un obstacle à contourner.
**Alternative rejetée** : merger automatiquement quand la CI est verte (une CI verte dit que le code passe, pas qu'il est bon) ; pousser en `--force` pour éviter les rejets (le rejet est l'information).
**Détail** : voir `tickets/done/ticket-064-agent-workflow-github.md`.

---

## ADR-023 — Le mode des artefacts échoue fermé

**Date** : 2026-09-16
**Décision** : `local` est le défaut quand `agents.json` ne déclare rien, est illisible ou absent, et le défaut d'origine de tout projet **sauf** un projet créé par l'IDE. Les projets importés rejoignent les clonés. `init_repository` applique le mode déclaré avant son `git add -A`.
**Raison** : ADR-021 posait le mécanisme mais le faisait dépendre d'une déclaration, et `default_mode_for` n'était câblé que sur le clone. Les deux erreurs ne sont pas symétriques : des artefacts non versionnés se rattrapent d'un clic, un push dans le dépôt d'un client ne se défait pas. Le défaut protège, le partage se déclare.
**Alternative rejetée** : garder `tracked` (fait reposer la confidentialité sur un fichier qui peut manquer) ; avertir sans changer le défaut (l'avertissement arrive après le push).
**Limite** : `.git/info/exclude` n'agit que sur le non-suivi. Un dépôt qui versionne déjà un `CLAUDE.md` en commitera les modifications — c'est ce que `tracked_artifact_paths()` remonte.

---

## ADR-024 — Un projet doit être la racine de son propre dépôt

**Date** : 2026-09-16
**Décision** : `GitWorkspaceService` vérifie, avant toute création de branche, que `git rev-parse --show-toplevel` renvoie exactement le dossier du projet. Sinon il lève `NotAGitRepository` et le run s'arrête.
**Raison** : `--is-inside-work-tree` réussit aussi quand le dépôt trouvé est un **ancêtre**. Un dossier client posé dans `projects/` sans dépôt à sa racine faisait remonter git jusqu'au dépôt de vibe-ide : le run créait sa branche et son commit dans l'IDE, au nom du projet du client. La classe promettait « never on vibe-ide itself » sans rien qui le garantisse.
**Conséquence** : un dossier qui regroupe plusieurs dépôts n'est pas un projet. Chaque dépôt doit être déclaré comme son propre projet.
**Alternative rejetée** : `git init` automatique à la racine (crée un dépôt non désiré au-dessus de ceux du client) ; descendre chercher le premier sous-dépôt (choix arbitraire dès qu'il y en a plusieurs).

---

## ADR-025 — Une question sans réponse reprend sur une hypothèse énoncée

**Date** : 2026-09-16
**Décision** : Un agent peut suspendre son tour pour poser une question. Passé `dialogue_timeout_s`, il reprend seul : on lui répond qu'aucun humain n'est disponible et qu'il doit **choisir et énoncer son hypothèse**. En mode autonome, le délai ne démarre pas.
**Raison** : ADR-018 fait dépendre la file des tickets d'un arbre propre, et un run suspendu tient du travail non commité : une question sans réponse le temps d'un déjeuner bloquerait la file. Une hypothèse explicite, qui part dans le rapport du run, est relisible ; une hypothèse silencieuse — l'état d'avant — ne l'est pas.
**Corollaire** : les messages spontanés ont une file **distincte**, vidée entre deux tours dans `build_context` : un « pense aux tests » ne doit jamais valoir réponse à « on casse l'API ? ».
**Alternative rejetée** : attendre indéfiniment (bloque la file) ; laisser l'agent trancher seul en silence (le défaut d'origine) ; déduire la réponse d'un message spontané.

---

## ADR-026 — Cinq familles de couleurs, une par rôle

**Date** : 2026-09-17
**Décision** : Toutes les bandes d'en-tête de premier niveau partagent une hauteur unique (`design/layout.ts`). L'UI n'utilise que `zinc` (neutre), `red` (échec), `amber` (attente), `green` (succès) et `blue` (activité) pour les **états**, plus `violet` pour l'**identité et le repérage** — barre devant un titre de région, élément actif du rail, nom du projet. Les tailles de texte sont nommées, jamais arbitraires, et les affordances viennent de `design/icons.tsx`, sur une grille unique. Un test (`design/coherence.test.ts`) verrouille les trois règles.
**Raison** : l'UI avait dérivé vers huit familles — `green` et `emerald` disaient la même chose, `amber`, `orange` et `yellow` aussi — trois tailles en dur et des glyphes de jeux différents. Personne n'avait choisi huit couleurs : chaque ticket prenait la sienne. Sans mesure, la dérive ne se voit qu'une fois qu'elle saute aux yeux.
**Conséquence** : l'accent d'identité est une barre, jamais la couleur d'un mot — du violet sur du texte se lirait comme un état de plus. Une priorité moyenne ou basse n'est pas une alerte ; elle descend en neutre et se distingue par l'intensité, pas par la teinte. Les badges GitHub sont des métadonnées, donc neutres.
**Alternative rejetée** : une couche d'alias sémantiques (`text-success`) — elle ajoute une indirection sans rien changer à l'écran ; documenter les rôles sans les vérifier (c'est ce qui n'a pas tenu).

---

## ADR-027 — Les agents ne touchent pas à l'historique git

**Date** : 2026-09-17
**Décision** : Un hook `PreToolUse` refuse à tout agent les commandes git qui écrivent — `commit`, `merge`, `push`, `checkout`, `branch`, `reset`, `rebase`, `add`, `remote`… Le git en lecture reste permis. Et un run dont le commit **échoue** ne peut pas s'annoncer approuvé : le ticket passe `blocked`, avec la raison émise.
**Raison** : au premier usage réel, des agents ont commité avec leurs propres messages, mergé la branche de ticket dans `main` et poussé sur GitHub — pendant deux runs où l'utilisateur n'avait cliqué que sur « lancer ». ADR-018 et ADR-022 ne contraignaient que `GitWorkspaceService` ; le codeur a `Bash` et pouvait faire du git sans passer par elle. Une règle contournable en tapant une autre commande n'est pas une règle.
**Pourquoi un hook et pas `can_use_tool`** : une entrée d'`allowed_tools` couvrant un outil entier — le cas de `Bash` — l'auto-approuve *avant* le callback de permission. Le garde y serait inerte, avec l'apparence d'une protection.
**Alternative rejetée** : l'interdire dans le prompt (une consigne décrit une intention, un refus produit un fait) ; retirer `Bash` au codeur (il en a besoin pour lancer des tests et inspecter le projet).
**Détail** : voir `tickets/done/ticket-068-integrite-des-runs.md`.

---

## ADR-028 — Travailler dans le dépôt parent se déclare

**Date** : 2026-09-17
**Décision** : ADR-024 refuse par défaut qu'un projet agisse sur un dépôt **ancêtre**. Un projet peut lever ce refus en déclarant `"git_root": "ancestor"` dans son `agents.json` ; il stage alors depuis la racine du dépôt (`:/`) et non depuis son propre dossier. Seule cette valeur exacte ouvre l'exception.
**Raison** : ADR-024 est né d'un dossier client posé dans `projects/`, dont le dépôt ancêtre était vibe-ide — un accident. Mais c'est exactement ce que fait le projet bootstrap d'ADR-001 : il construit l'IDE, donc il travaille volontairement dans le dépôt qui le contient, et son travail est dans `backend/` et `frontend/`, au-dessus de lui. Traiter les deux cas pareil supprimait l'auto-hébergement, c'est-à-dire le principe fondateur.
**Forme** : la même que pour le mode des artefacts (ADR-021, ADR-023) — le défaut protège, le cas particulier s'énonce dans le fichier du projet. Une valeur inconnue ne désarme rien.
**Détail** : voir `tickets/done/ticket-077-auto-hebergement.md`.

