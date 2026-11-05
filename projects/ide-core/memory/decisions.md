# Décisions d'architecture

Ce fichier trace les décisions importantes et leur justification, dans
l'ordre où elles ont été prises — pas par sujet. Un ADR **sans `Portée`** est
une contrainte pour tous les agents ; une portée ne marque qu'un choix passé.

Une ADR qu'aucune règle de `contraintes.md` ni aucun `CLAUDE.md` ne cite part dans
`decisions-archive.md`, son numéro inchangé (ticket-830).

---

## ADR-006 — ProjectLoader filtre sur CLAUDE.md

**Date** : 2026-06  
**Portée** : architect, codeur, reviewer  
**Décision** : `ProjectLoader.list_projects()` ne liste que les dossiers contenant un `CLAUDE.md`, tandis que `list_projects()` (module-level) liste tous les dossiers.  
**Raison** : L'orchestrateur ne doit travailler que sur des projets structurés. La fonction module-level reste disponible comme utilitaire bas niveau pour les tests et scripts.  
**Alternative rejetée** : Filtrer aussi dans la fonction module-level (casserait les tests existants sans apport réel).

---

## ADR-007 — Modèle de projet : `name` parsé depuis le H1 du CLAUDE.md

**Date** : 2026-06  
**Portée** : architect, codeur, reviewer  
**Décision** : Le champ `name` d'un `Project` est extrait de la première ligne `# Titre` du CLAUDE.md, avec fallback sur le nom du dossier.  
**Raison** : Le nom du dossier est un identifiant technique (`ide-core`) ; le titre H1 est le nom lisible (`CLAUDE.md — projet ide-core`). Les deux coexistent.  
**Alternative rejetée** : Utiliser uniquement le nom du dossier comme `name` (perd l'intention du CLAUDE.md).

---

## ADR-008 — Orchestrateur sans état interne (stateless)

**Date** : 2026-06  
**Portée** : architect, codeur, reviewer  
**Décision** : `Orchestrator` est instancié à chaque requête HTTP (pas de singleton). Il reçoit `AgentRunner`, `TicketService` et `project_context` en injection de dépendances. Ce qui survit à une requête vit **hors** de lui : `RunLock` et `RunRegistry`, en mémoire du process.  
**Raison** : deux pipelines sur des projets différents tournent en parallèle sans rien partager. Mais « zéro lock » ne vaut qu'**entre** projets : sur un même arbre, `RunLock` refuse le second run (ADR-038).  
**Alternative rejetée** : Singleton avec un dictionnaire de verrous par ticket — trop complexe pour la v0.

---

## ADR-009 — Verdict reviewer : parseur par mot-clé retiré (ADR-061)

**Date** : 2026-06  
**Portée** : architect, codeur, reviewer  
**Décision** : L'orchestrateur ne lit plus le texte du reviewer (amendé 2026-10-28, ticket-614) : il lit `verdict`, `summary` et `blocking[{text, location, confidence}]` dans la sortie structurée d'ADR-061. Un `CHANGES_REQUESTED` dont **toutes** les remarques sont sous `reviewer_confidence_threshold` (80 par défaut, 0 = filtre éteint) est lu comme une approbation avec remarques (ticket-574). Une sortie absente ou hors schéma, ou un `APPROVED` avec une remarque au-dessus du seuil, refuse.  
**Raison** : le parseur par mot-clé a coûté trois rustines (tickets 122, 298, 574) ; un champ typé le remplace.  
**Alternative rejetée** : garder le mot-clé en repli — une réponse ambiguë approuverait.

---

## ADR-010 — github-sync intégré dans POST /agents/run (pas d'endpoint dédié)

**Date** : 2026-06  
**Portée** : architect, codeur, reviewer  
**Décision** : `role: github-sync` est géré dans `POST /api/v1/agents/run` avec court-circuit avant le lookup ticket. Retourne un `AgentResult` synthétique.  
**Raison** : Cohérence du contrat API — un seul endpoint pour tous les rôles. `AgentResult.created_tickets` porte déjà le payload utile. `ticket_id` est rendu optionnel (default `""`) pour accommoder les rôles sans ticket cible.  
**Alternative rejetée** : Endpoint dédié `/agents/github-sync` — fragmentation de l'API sans bénéfice pour la v0.

---

## ADR-012 — Monaco bundlé localement (pas CDN)

**Date** : 2026-06-20
**Portée** : architect, codeur  
**Décision** : Monaco Editor chargé depuis le package npm `monaco-editor`, bundlé via Vite. Pas de CDN jsdelivr.
**Raison** : Les builds Tauri packagés n'ont pas d'accès internet (app distribuée offline). Le CDN fonctionnerait en dev mais casserait en production desktop.
**Alternative rejetée** : CDN uniquement (acceptable en web, inutilisable en desktop packagé).

---

## ADR-013 — Hooks React sans gestionnaire d'état global

**Date** : 2026-06-20
**Portée** : architect, codeur, reviewer  
**Décision** : Pas de Zustand/Jotai pour la v0. L'état partagé (projet actif, ticket actif) tient dans `useActiveProject`. Les autres hooks sont autonomes.
**Raison** : Le graphe d'état de la v0 est simple — 2 entités partagées. Ajouter un store serait du surengineering prématuré.
**Alternative rejetée** : Zustand (à réévaluer si on dépasse 5 états globaux partagés entre composants non-parents).

---

## ADR-014 — Vitest + React Testing Library pour les tests frontend

**Date** : 2026-06-20
**Portée** : architect, codeur  
**Décision** : Vitest pour l'exécution + RTL pour les assertions composants.
**Raison** : Vitest partage la config Vite (transforms, aliases, ESM) sans configuration séparée. RTL encourage les tests par comportement utilisateur, pas par implémentation.
**Alternative rejetée** : Jest (configuration babel séparée, pas d'ESM natif, overhead de setup).

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
**Décision** : chaque run s'exécute sur sa propre branche, relit le **diff git réel** plutôt que la prose du codeur, et finit toujours par un commit — typé du ticket si approuvé, `chore: … — unapproved work (…)` sinon. Seul un run approuvé avance la ref de base.
**Raison** : depuis ADR-017 les agents écrivent vraiment sur disque ; relire leur prose validait une intention, pas une implémentation. Committer à tous les coups garde l'arbre propre pour le ticket suivant sans perdre le travail rejeté. N'avancer la base que sur approbation donne l'isolation **et** l'empilement d'un plan séquentiel.
**Alternative rejetée** : laisser l'arbre sale pour inspection — bloque le ticket suivant ; `wip:` en préfixe — pas un type Conventional Commits.
**Conséquence assumée** : du code bloqué par l'audit sécurité entre dans l'historique, confiné à la branche du ticket, jamais sur `main`.

## ADR-019 — Le chat de l'IDE commite comme un run de pipeline

**Date** : 2026-09-15
**Décision** : le chat conversationnel écrit sur une branche `chat-<horodatage>` et commite son travail, comme un run le fait sur sa branche de ticket. Il ne laisse jamais l'arbre sale.
**Raison** : ADR-018 fait reposer l'enchaînement des tickets sur un arbre propre au démarrage. Un chat qui écrit sans committer enverrait le ticket suivant en `blocked` sans qu'aucun agent n'ait tourné. Traiter le chat comme un producteur de travail de première classe évite d'inventer un second régime d'écriture à côté de celui du pipeline.
**Alternative rejetée** : limiter le chat aux fichiers hors arbre suivi — sûr, mais en fait un outil de seconde classe ; poser un verrou qui empêche le pipeline de démarrer — sérialise deux choses qui travaillent sur des branches distinctes. Une branche `chat/*` de trop se supprime ; un arbre cassé bloque la file.

## ADR-020 — Deux plafonds distincts : dépense estimée et quota réel

**Date** : 2026-09-15
**Décision** : un run autonome s'arrête sur **deux** conditions indépendantes, vérifiées entre deux tickets : la dépense cumulée estimée (`RUN_MAX_BUDGET_USD`) et le quota d'abonnement réel remonté par le fournisseur (`QuotaTracker`). Un quota **inconnu** ne bloque jamais.
**Raison** : les deux mesurent des choses différentes. La dépense se calcule depuis les tokens et une grille tarifaire ; le quota est une fenêtre glissante imposée par le fournisseur, qui peut couper un run alors qu'aucun plafond local n'a bougé. Ne suivre que l'un laisse l'autre panne intacte.
**Alternative rejetée** : déduire le quota de la dépense — les deux ne sont pas proportionnels ; traiter l'absence d'événement comme un quota nul — un fournisseur muet deviendrait indiscernable d'un quota épuisé.
**Invariant** : la vérification se fait **entre** deux tickets. S'arrêter au milieu de l'un laisserait son travail non commité, ce qu'ADR-018 interdit.

## ADR-021 — Les artefacts Tessera s'excluent par `.git/info/exclude`, jamais par `.gitignore`

**Date** : 2026-09-15
**Décision** : un projet déclare dans `agents.json` si ses `tickets/`, `memory/`, `CLAUDE.md` et `agents.json` partent dans son dépôt (`tracked`) ou restent sur la machine (`local`). En mode `local`, l'exclusion s'écrit dans `.git/info/exclude`, entre marqueurs, et **jamais** dans `.gitignore`.
**Raison** : `.gitignore` est lui-même versionné. Le modifier sur un dépôt tiers produit un diff visible qui annonce exactement ce qu'on voulait garder hors du dépôt. `.git/info/exclude` a la même sémantique, reste local au clone, et n'apparaît ni dans l'historique ni dans un diff.
**Alternative rejetée** : un réglage global — le bon choix dépend du projet, pas de la machine ; retirer de l'index les artefacts déjà suivis, car `git rm --cached` modifie l'historique à venir du dépôt de l'utilisateur : ça se propose, ça ne se fait pas en silence.

## ADR-022 — L'agent de workflow pousse et ouvre la PR

**Date** : 2026-09-15
**Décision** : `GitHubWorkflowService` pousse la branche du ticket puis ouvre sa PR. Le push n'est **jamais** forcé. Le merge, lui, ne s'interdit plus partout : il se déclare par projet (ADR-029).
**Raison** : merger, c'est décider qu'un travail est bon — sur un dépôt tiers, c'est le point où un humain tranche. Quant au push : écraser une référence distante peut détruire du travail qui n'est pas le nôtre. Un push refusé est une décision à remonter, pas un obstacle à contourner.
**Alternative rejetée** : pousser en `--force` pour éviter les rejets — le rejet **est** l'information.

## ADR-023 — Le mode des artefacts échoue fermé

**Date** : 2026-09-16
**Décision** : `local` est le défaut quand `agents.json` ne déclare rien, est illisible ou absent, et le défaut d'origine de tout projet **sauf** un projet créé par l'IDE.
**Raison** : ADR-021 posait le mécanisme mais le faisait dépendre d'une déclaration. Les deux erreurs ne sont pas symétriques : des artefacts non versionnés se rattrapent d'un clic, un push dans un dépôt tiers ne se défait pas. Le défaut protège, le partage se déclare.
**Alternative rejetée** : garder `tracked` — fait reposer la confidentialité sur un fichier qui peut manquer ; avertir sans changer le défaut — l'avertissement arrive après le push.
**Limite** : `.git/info/exclude` n'agit que sur le non-suivi. Un dépôt qui versionne déjà un `CLAUDE.md` en commitera les modifications ; c'est ce que `tracked_artifact_paths()` remonte.

## ADR-024 — Un projet doit être la racine de son propre dépôt

**Date** : 2026-09-16
**Décision** : `GitWorkspaceService` vérifie, avant toute création de branche, que `git rev-parse --show-toplevel` renvoie exactement le dossier du projet. Sinon il lève `NotAGitRepository` et le run s'arrête.
**Raison** : `--is-inside-work-tree` réussit aussi quand le dépôt trouvé est un **ancêtre**. Un dossier tiers dans `projects/` sans dépôt propre fait remonter git jusqu'au dépôt de Tessera : le run crée sa branche dans l'IDE au lieu de celle du projet. La classe promettait « never on Tessera itself » sans rien qui le garantisse.
**Conséquence** : un dossier qui regroupe plusieurs dépôts n'est pas un projet. Chaque dépôt doit être déclaré comme son propre projet.
**Alternative rejetée** : `git init` automatique à la racine (crée un dépôt non désiré au-dessus de ceux du projet) ; descendre chercher le premier sous-dépôt (choix arbitraire dès qu'il y en a plusieurs).

---

## ADR-025 — Une question sans réponse reprend sur une hypothèse énoncée

**Date** : 2026-09-16
**Décision** : un agent peut suspendre son tour pour poser une question. Passé `dialogue_timeout_s`, il reprend seul : on lui répond qu'aucun humain n'est disponible et qu'il doit **choisir et énoncer son hypothèse**. En mode autonome, le délai ne démarre pas.
**Raison** : ADR-018 fait dépendre la file d'un arbre propre, et un run suspendu tient du travail non commité : une question laissée le temps d'un déjeuner bloquerait la file. Une hypothèse explicite, qui part dans le rapport du run, est relisible ; une hypothèse silencieuse — l'état d'avant — ne l'est pas.
**Corollaire** : les messages spontanés ont une file **distincte**, vidée entre deux tours. Un « pense aux tests » ne doit jamais valoir réponse à « on casse l'API ? ».

## ADR-026 — Cinq familles de couleurs, une par rôle

**Date** : 2026-09-17
**Portée** : codeur, reviewer
**Décision** : les **états** n'utilisent que `zinc` (neutre), `red` (échec), `amber` (attente), `green` (succès), `blue` (activité) ; `violet` sert à l'**identité** et à l'**interaction** — titre de région, sélection, action principale. Bandes d'en-tête de hauteur unique, tailles de texte nommées, affordances dans `design/icons.tsx`. Un test verrouille ces règles.
**Raison** : l'UI avait dérivé vers huit familles, trois tailles en dur et des glyphes de jeux différents. Personne n'avait choisi huit couleurs : chaque ticket prenait la sienne, et sans mesure la dérive ne se voit qu'une fois qu'elle saute aux yeux.
**Conséquence** : le violet s'emploie en **fond ou en barre**, jamais en couleur de texte — du violet sur un mot se lirait comme un état de plus. Seule exception, les liens soulignés du Markdown rendu, définis dans `index.css` (amendé 2026-09-30, ticket-248).

## ADR-027 — Les agents ne touchent pas à l'historique git

**Date** : 2026-09-17
**Décision** : un hook `PreToolUse` refuse à tout agent le git et le `gh` qui écrivent, quelle que soit la tournure — chemin, casse, enveloppe, alias. Le git en lecture reste permis. Les fichiers qui portent la politique du run — `agents.json`, `.git/`, `.claude/settings*.json`, `.github/workflows/` — se refusent en écriture ; la politique se lit une fois, avant le premier agent ; l'orchestrateur n'exécute jamais les hooks du dépôt. Un commit qui **échoue** n'approuve pas le run.
**Raison** : au premier usage réel, des agents ont commité, mergé et poussé sur un simple « lancer ». Le codeur a `Bash` : une règle contournable en tapant une autre commande n'en est pas une. Un hook, parce qu'`allowed_tools` auto-approuve *avant* le callback de permission.
**Limite** : il attrape une erreur et les tournures triviales, pas une évasion — `python -c` passe (ADR-031).

## ADR-028 — Travailler dans le dépôt parent se déclare

**Date** : 2026-09-17
**Décision** : ADR-024 refuse par défaut qu'un projet agisse sur un dépôt **ancêtre**. Un projet lève ce refus en déclarant `"git_root": "ancestor"` dans son `agents.json` ; il stage alors depuis la racine du dépôt (`:/`). Seule cette valeur exacte ouvre l'exception.
**Raison** : ADR-024 protège contre un dossier tiers dans `projects/` dont git remonterait jusqu'au dépôt de Tessera. Mais c'est exactement ce que fait le projet bootstrap d'ADR-001 : il construit l'IDE, donc il travaille volontairement dans le dépôt qui le contient, et son travail est dans `backend/` et `frontend/`, au-dessus de lui. Traiter les deux cas pareil supprimait l'auto-hébergement, c'est-à-dire le principe fondateur.
**Forme** : celle d'ADR-021 et ADR-023 — le défaut protège, le cas particulier s'énonce. Une valeur inconnue ne désarme rien.

## ADR-029 — Jusqu'où l'agent va se déclare par projet

**Date** : 2026-09-18
**Décision** : `agents.json` porte un champ `autonomy` : `commit` (défaut — le travail reste sur sa branche), `pr` (pousse et ouvre la PR), `merge` (merge aussi, **si et seulement si** la CI est verte). Valeur absente ou inconnue : `commit`. Le niveau borne ce que l'IDE fait **seul** ; le même geste demandé depuis l'IDE reste la décision de l'utilisateur.
**Raison** : le raisonnement d'ADR-022 — merger, c'est décider qu'un travail est bon — tient sur un dépôt tiers, où les accès sont spécifiques et où l'utilisateur pousse lui-même. Il ne vaut pas sur un dépôt personnel doté d'une CI : y refuser le merge ne protège personne, ça ajoute un clic.
**Alternative rejetée** : un réglage global — le bon niveau dépend du dépôt ; merger sur une CI absente ou en cours — l'absence de signal n'est pas un signal favorable.

## ADR-030 — La livraison est une étape à part, et elle ne fait jamais échouer le run

**Date** : 2026-09-18
**Décision** : après un run **approuvé**, `LivraisonService` enchaîne seul : rebase sur la base, PR (qui referme son issue par `Closes #N`), attente de CI bornée, merge — chaque maillon soumis au niveau d'ADR-029. L'appel est branché dans `run_pipeline`, donc sur les trois modes. Une exception y est capturée et rendue dans `Livraison.arret` ; le run garde son résultat.
**Raison** : les maillons existaient tous, rien ne les enchaînait, et chaque étape demandait un clic. Mais le travail est déjà commité quand la livraison commence : faire échouer le run parce que GitHub est injoignable ferait croire que le pipeline a échoué.
**Invariants** : un run non approuvé ne se livre jamais ; un conflit annule le rebase au lieu de laisser l'arbre à mi-chemin ; l'attente de CI est bornée — sinon la file se bloque.

## ADR-031 — Un agent n'écrit que sous la racine de son projet

**Date** : 2026-09-18
**Décision** : un hook `PreToolUse` refuse `Write`, `Edit`, `NotebookEdit` et les redirections `Bash` simples (`>`, `>>`, `tee`) dont le chemin sort de la racine du projet — son dossier, ou le dépôt qui le contient s'il déclare `git_root: ancestor`. Les deux côtés sont résolus, symlinks compris. **Lire hors du projet reste permis.**
**Raison** : `cwd` place l'agent dans le projet, il ne l'y enferme pas. Plusieurs dépôts tiers voisins dans `projects/`, et un agent qui se trompe de dossier écrit dans le mauvais — la fuite qu'ADR-021 et ADR-023 empêchent, prise par l'autre bout.
**Ce que ça ne garantit pas** : le contrôle sur `Bash` attrape une erreur, pas une évasion — `python -c "open('../x','w')"` passe. Ce qui ne se lit pas avec certitude passe aussi : un faux refus priverait l'agent de son moyen de vérifier son travail.

## ADR-033 — Un conflit se tente, et se relit toujours

**Date** : 2026-09-18
**Décision** : sur un conflit de rebase, un agent `resolveur-conflit` réécrit les fichiers. `GitWorkspaceService` vérifie ensuite l'arbre et **annule tout** au moindre doute : résolveur qui lève, marqueur restant, fichier manquant. Une résolution qui aboutit ouvre sa PR et **ne se merge jamais seule**, même sur un projet en `merge`.
**Raison** : détecter et rendre la main était honnête, mais s'arrêtait sur un travail de cinq minutes. Le tenter vaut la peine ; le merger, non. Un conflit est par définition l'endroit où deux intentions divergent : le pire endroit pour deviner, et celui où une erreur ne se voit pas dans un diff vert.
**Invariants** : l'arbre ne reste jamais à mi-rebase ; l'agent ne touche à aucune commande git, le rebase est en cours et il n'en voit qu'une partie.

---

## ADR-035 — La documentation se met à jour par lot, en modifications ciblées

**Date** : 2026-09-18
**Portée** : architect
**Décision** : après chaque run **approuvé**, sur sa branche et avant sa livraison, `doc-technique` et `doc-fonctionnelle` reçoivent les tickets livrés depuis le dernier marqueur (amendé 2026-09-26 : en fin de file, elle restait sur le disque sans commit). Ils rendent des **modifications** : un ancien texte exact, un nouveau. Un ancien absent, ambigu, ou qui amputerait le fichier de moitié rejette tout le lot sans rien écrire.
**Raison** : `doc-updater` réécrivait le fichier **entier** depuis une vue tronquée à 8 000 caractères. Sur un `README.md` de 24 000 caractères, il en aurait effacé les deux tiers sans erreur — le contrat ne lui laissait pas le choix.
**Pourquoi deux agents** : un seul écrit un guide utilisateur plein de noms de classes — c'est ce qu'il vient de lire.

---

## ADR-037 — Une panne de production ne fait pas perdre le travail

**Date** : 2026-09-21
**Décision** : une exception levée pendant la production termine le run en `blocked`, commite le travail écrit sous `chore: … — unapproved work (…)` et rend la cause dans `PipelineResult.arret`. Jamais une erreur serveur.
**Raison** : le premier run coupé par le plafond du fournisseur a remonté son exception jusqu'à FastAPI : aucun commit, arbre sale, run jamais clos. ADR-020 vérifie ses plafonds **entre** deux tickets pour ne pas laisser de travail non commité ; celui-là coupe au milieu d'un tour. Or ADR-018 fait dépendre le ticket suivant d'un arbre propre.
**Alternative rejetée** : propager — l'état d'avant, qui bloque la file ; jeter le travail — déjà payé, et le relire coûte moins que le refaire.
**Conséquence assumée** : un commit peut figer du code à moitié écrit. Le message nomme la panne, sans quoi il se relit comme un abandon.

---

## ADR-038 — Un projet ne porte qu'un run à la fois, et chaque sortie commite

**Date** : 2026-09-22
**Décision** : un verrou en mémoire, partagé par tous les points d'entrée — run unique, file, autonome, chat — refuse un second run sur un projet occupé (409, en nommant le ticket en cours). Deux projets tournent en parallèle. Chaque sortie du pipeline commite ; un commit raté rend `blocked` avec `arret`, jamais une exception. Un émetteur d'événements qui lève n'interrompt pas le run.
**Raison** : ADR-008 rend l'orchestrateur stateless — deux runs sur le **même** arbre passaient `ensure_clean_tree` avant que le second déplace la branche sous le premier. Et `CommitFailed` n'était attrapé que sur le chemin approuvé : ailleurs, l'exception remontait jusqu'à FastAPI, arbre sale, run jamais clos.
**Alternative rejetée** : une file d'attente — qui clique deux fois veut savoir, pas attendre ; un verrou en base — un backend local n'a pas de second process à protéger.

---

## ADR-039 — Une porte du pipeline qui n'a pas pu juger refuse

**Date** : 2026-09-22
**Décision** : l'audit sécurité et la validation **échouent fermés** : provider indisponible, réponse illisible ou exception dans l'étape rendent `BLOCK` / `CHANGES_REQUESTED`, jamais un passage. Une faille `CRITICAL` ou `HIGH` bloque quel que soit le verdict énoncé par le LLM. La cause part dans l'événement (`reason`), lisible à l'écran.
**Raison** : ces étapes existent pour arrêter du code. Une panne qui les fait passer retire la protection là où elle se voit le moins : rien à l'écran ne distingue un audit propre d'un audit qui n'a pas eu lieu. Le validateur refusait déjà un JSON illisible mais approuvait sur un provider en panne.
**Alternative rejetée** : sauter l'étape et prévenir — l'avertissement part dans un log pendant qu'un `done` s'affiche.
**Conséquence assumée** : une panne du fournisseur bloque les runs qui activent ces étapes ; c'est voulu, le `reason` le dit.

---

---

## ADR-040 — Le shell desktop n'ouvre aucune porte vers le disque

**Date** : 2026-09-22
**Décision** : l'app Tauri n'expose ni commande fichier ni permission `fs:*` / `shell:*` ; le frontend passe toujours par `routers/fs.py`, packagé compris. L'origine du backend vient de `VITE_API_URL` au build, et le backend lancé par le shell n'écoute que sur `127.0.0.1`. ADR-016 n'a plus d'objet.
**Raison** : `read_file` / `write_file` / `list_dir` acceptaient n'importe quel chemin, quand l'API refuse tout ce qui sort du workspace. Le trou `?path=~/.ssh/id_rsa` rebouché d'un côté restait ouvert de l'autre : entre deux portes, c'est la moins gardée qui compte.
**Alternative rejetée** : porter le contrôle de chemin en Rust — deux implémentations d'une même règle divergent (ADR-034) ; garder `fs:*` « au cas où » — une permission que rien n'utilise est une surface sans bénéfice.
**Conséquence assumée** : le backend n'est pas embarqué ; l'app packagée exige `uv` et `TESSERA_BACKEND_DIR`.

---

## ADR-041 — Un run est observé, pas possédé

**Date** : 2026-09-23
**Portée** : architect, codeur, reviewer
**Décision** : un run démarre par `POST /orchestrator/run` et s'observe sur `WS /orchestrator/observe`, canal unique, tous projets confondus. `RunRegistry` tient les runs vivants et leur canal de dialogue ; `EventHub` diffuse, jetant le texte plutôt qu'une transition quand un client décroche. La WebSocket de lancement disparaît.
**Raison** : la socket qui lançait le run en était l'unique destinataire. Fermer l'onglet rendait aveugle, rien ne montrait le parallélisme entre projets (ADR-038), et seul cet onglet pouvait répondre à un agent (ADR-025). Se reconnecter relançait le travail — trois runs en double le 2026-09-17.
**Alternative rejetée** : diffuser une copie sans découpler — le run resterait lié à son lanceur ; tout pousser à tous — le navigateur lâche avant le backend.
**Conséquence assumée** : ADR-025 change de transport, pas de sémantique. `run_closed` dit la fin **et** la libération du projet.

---

## ADR-042 — Un projet se lance par une commande déclarée, jamais devinée

**Date** : 2026-09-23
**Décision** : un projet déclare dans `agents.json` une liste `services` de `{nom, commande}`. L'IDE les lance — sans shell, sans agent — dans un groupe que le système tue avec le backend, même tué brutalement. Leur sortie part sur le canal d'ADR-041. Rien de déclaré : pas de bouton.
**Raison** : les projets décrivent leur démarrage dans des sections aux noms différents, mêlé aux commandes de test : y choisir, c'est deviner. Confier `Bash` à un agent rouvrirait ce qu'ADR-027 et ADR-031 ferment mal — leur contrôle attrape une erreur, pas une évasion.
**Alternative rejetée** : détacher le processus, ou s'en remettre au seul arrêt propre — un backend tué n'exécute rien, et laissait vingt-deux orphelins.
**Conséquence assumée** : l'IDE ne prépare rien ; `npm ci` reste à la main. Hors Windows, seul l'arrêt propre tue les services.

---

## ADR-043 — Rien de professionnel n'entre dans un dépôt personnel

**Date** : 2026-09-23
**Décision** : un dépôt personnel ne reçoit aucune donnée professionnelle — nom de client, adresse e-mail d'employeur ou de client, identifiant, jeton, hostname interne. La règle porte sur le contenu **et** sur les métadonnées git : auteur, committer, trailers `Co-authored-by`. L'identité git se déclare par dossier (`includeIf`), jamais globalement.
**Raison** : un `user.email` global écrit sur tous les dépôts d'une machine sans jamais se rappeler à l'attention : un dépôt personnel rendu public expose ces métadonnées, et personne ne les relit avant de pousser.
**Alternative rejetée** : nettoyer après coup — un dépôt public est moissonné avant d'être corrigé, et un force-push laisse les objets joignables par leur SHA.
**Conséquence assumée** : réparer coûte la réécriture de l'histoire et la perte des PR.

---

## ADR-044 — Ce qu'une machine lit s'écrit en anglais

**Date** : 2026-09-25
**Décision** : identifiants, docstrings, noms de tests, messages de commit et titres de pull request s'écrivent en **anglais** — ici comme dans les projets que l'IDE construit. Commentaires, ADR, tickets et prompts restent en français.
**Raison** : ce dépôt s'adresse à des lecteurs inconnus, qu'un identifiant français arrête d'emblée. La règle existait à moitié — « docstrings en anglais » — et la pratique avait dérivé jusqu'aux titres de PR.
**Alternative rejetée** : tout traduire, ADR et prompts compris : ceux-là partent dans chaque appel d'agent, les traduire changerait le comportement du produit et non sa lisibilité. Ne rien normaliser : une base à moitié anglaise ne donne aucune règle sur laquelle s'appuyer.
**Conséquence assumée** : trois modules et cinq cents noms de tests restent à renommer. Sans CI, ce renommage se paierait en silence : il attend son retour.

---

## ADR-045 — Un dépôt sans CI merge sur le verdict du pipeline

**Date** : 2026-09-25
**Décision** : un projet déclare `merge_without_ci: true` dans `agents.json`. À `autonomy: merge`, la livraison n'attend alors aucune CI et merge sur le seul verdict du pipeline. Une CI qui répond `failing` ou `pending` refuse toujours.
**Raison** : ADR-029 lie le merge à une CI verte, jugeant le clic humain inutile sur un dépôt personnel **doté** d'une CI. Le cas sans CI n'était pas prévu : la pull request sert l'historique et les tests, pas à faire cliquer, et quatre agents ont déjà jugé — dont deux portes qui échouent fermées (ADR-039).
**Alternative rejetée** : ignorer une CI qui existe — merger par-dessus un rouge reste faux ; un réglage global — le bon choix dépend du dépôt, comme l'autonomie.
**Conséquence assumée** : sur un dépôt déclaré, plus rien d'humain ne s'interpose entre l'approbation et `main`.


---

## ADR-046 — Le provider se déclare par rôle, et un repli se voit

**Date** : 2026-09-26
**Décision** : chaque rôle déclare dans `agents.json` son `provider`, son `model`, et un `fallback` explicite (`provider` + `model`). Toute construction de provider passe par `provider_pour_role` ; un routeur n'appelle jamais `get_provider`. Seule une **indisponibilité** — connexion refusée, délai, modèle absent — déclenche le repli, qui émet `provider_fallback` sur le canal d'ADR-041. Une réponse illisible n'en déclenche aucun.
**Raison** : le provider était global et cinq services avaient leur modèle codé en dur : brancher un modèle local aurait basculé le codeur avec. Un repli silencieux masquerait un modèle qui ne tient pas ; ADR-039 exige que ce qui n'a pas pu juger refuse, pas qu'un autre juge à sa place sans le dire.
**Alternative rejetée** : router selon la charge ou la taille du ticket — deviné, donc invérifiable ; un réglage global de repli — le bon repli dépend du rôle.

---

## ADR-047 — Les graphiques ont leur palette, hors des couleurs d'état

**Date** : 2026-09-28
**Portée** : codeur, reviewer
**Décision** : trois teintes de données — `data-1` à `data-3` (cyan, indigo, magenta) — distinguent les séries d'un graphique, dans cet ordre fixe ; au-delà, « autres » en zinc. Elles ne s'emploient que dans `design/charts/`, et leurs familles jamais en brut. Une issue de run reste un état : couleurs d'ADR-026.
**Raison** : ADR-026 ne donne des couleurs qu'aux états et à l'identité. Colorer deux séries en bleu et vert les ferait lire comme « activité » et « succès ». Les trois teintes passent le contrôle daltonien et de contraste sur zinc-900 ; une quatrième ne le passe plus.
**Alternative rejetée** : une série colorée par graphique, le reste en zinc — deux séries superposées deviennent illisibles ; réutiliser `violet` — il marque l'identité, pas une donnée.

---

## ADR-048 — Vérifier les termes interdits avant tout push

**Date** : 2026-09-28
**Décision** : Avant tout push vers un dépôt distant, le backend contrôle les lignes ajoutées du diff, les messages de commit et les auteurs contre `FORBIDDEN_TERMS` (`.env` local, jamais versionné). Liste vide ou absente : aucun contrôle. Un terme trouvé bloque le push ; `Livraison.arret` signale la localisation sans nommer le terme. Un projet déclare `"confidentiality": "professional"` dans `agents.json` pour s'exempter ; défaut et valeur inconnue : contrôlé.
**Raison** : ADR-018 et ADR-027 font commiter l'orchestrateur lui-même — ni l'identité git par dossier ni un hook global ne couvrent ces commits. Le push est le seul point de contrôle avant que le contenu quitte la machine.
**Alternative rejetée** : contrôle au commit — ADR-018 exige un commit à chaque sortie, bloquer le commit casserait l'arbre propre ; hook pre-push global — ignoré pendant les runs (ADR-027).

---

## ADR-049 — Un rôle qui lit le web n'a pas de shell

**Date** : 2026-09-29
**Décision** : un rôle déclaré `"web": true` dans `agents.json` reçoit `WebFetch` et `WebSearch` et perd `Bash`, principal comme repli. `par_role.outils_du_role` est le seul endroit qui compose ces outils ; un rôle sans outils ne gagne rien.
**Raison** : une page lue peut porter des instructions, et on ne sait pas filtrer une page. Avec `Bash` et `acceptEdits`, l'agent aurait de quoi les exécuter — un `curl` suffit à faire sortir un fichier. Sans shell, une injection ne peut plus qu'écrire dans le périmètre, sous relecture.
**Alternative rejetée** : un MCP de documentation — une dépendance et un réseau de plus au démarrage, pour un besoin que le CLI couvre ; le web au codeur — c'est le rôle qui a le plus besoin de `Bash`.

---

## ADR-050 — Un terme interdit est arrêté à trois portes, et une porte qui n'a pas pu juger refuse

**Date** : 2026-09-29
**Décision** : `FORBIDDEN_TERMS` (`.env`, jamais versionné) est contrôlé au push du pipeline, par un hook `pre-push` en manuel, et en CI sur chaque PR — titre et corps compris — liste en secret GitHub, job requis par la protection des branches. Git en échec : refus, partout. Liste absente : refus en CI, où le secret se déclare ; en local, aucun contrôle (ADR-048), un clone neuf pousse (amendé 2026-09-29). Avant publication, `scripts/scan_historique.py` couvre l'historique et les métadonnées GitHub.
**Raison** : une seule porte se contourne sans le vouloir : push manuel, agent d'une autre session, corps de PR.
**Alternative rejetée** : la CI seule — elle voit la PR quand la branche est déjà publique.
**Conséquence assumée** : la liste vaut partout, son périmètre se déclare — `confidentiality: professional`, un CV qui cite ses employeurs.

---

## ADR-051 — Libérer l'arbre après la PR, pas après le merge

**Date** : 2026-10-02
**Décision** : `LivraisonService` se scinde. Phase 1 — rebase, push, PR — libère le verrou (ADR-038) via `run_closed` (ADR-041). Phase 2 — attente CI, merge — tourne dans `CIWatcher`, tâche de fond. Au plus une livraison en attente par projet. CI rouge : `blocked`, PR ouverte, sans relance (amendé 2026-10-02, ticket-304). Arrêt backend : PRs laissées ouvertes, sans reprise. `CI_MERGE_DONE` s'émet sur le canal projet. `depends_on` bloque le ticket suivant jusqu'au merge. Amende ADR-018, ADR-030, ADR-038.
**Raison** : N+1 forke depuis `origin/<base>` (ticket-285) sans le code de N. Conflits sur `decisions.md` et `pipeline-log.md` : committés avant le rebase (ticket-303), N+1 ne conflicte que si N est mergé et touche les mêmes lignes — même fréquence qu'aujourd'hui.
**Alternative rejetée** : reprise au redémarrage — état à persister, disproportionné ; sémaphore global — bloque deux projets indépendants.

---

## ADR-053 — Les jetons de mise en ligne ne quittent pas le backend

**Date** : 2026-10-16
**Décision** : seule une action de l'utilisateur crée les ressources en ligne d'un projet (Vercel, base, Resend, Stripe, Cloudflare), jamais un agent. Les jetons ne vivent que dans le `.env` de Tessera : aucun agent ne les reçoit ni ne lit ce fichier (amende ADR-031), aucun dépôt, ticket, journal ou réponse d'API ne les porte, les logs les masquent. Portée minimale : Stripe restreinte et en test, Vercel expirant, Cloudflare limité à la zone DNS. Relancer complète l'existant, sans doublon. Restent humains : comptes, achat du domaine, mode réel Stripe.
**Raison** : un jeton Vercel ouvre tout le compte, et ADR-031 laisse lire hors du projet : un agent lirait le `.env`.
**Alternative rejetée** : un agent qui déploie avec le jeton — le contrôle de `Bash` attrape une erreur, pas une évasion (ADR-031).

---

## ADR-055 — Un run n'écrit une règle commune que sous « Proposées »

**Date** : 2026-10-19
**Décision** : `contraintes.md` porte en tête une section `## Proposées` que le chargeur n'injecte dans aucun appel d'agent. Un diff de run qui modifie ce fichier hors de cette section met le run en `blocked` à la fin du tour du codeur, raison au journal. Une règle nouvelle s'écrit sous `## Proposées`, avec son ADR ; un humain l'accepte en la déplaçant dans sa section. `decisions.md` n'est pas concerné : il n'est injecté nulle part.
**Raison** : `contraintes.md` part dans chaque appel d'agent. Un run qui y ajoute une ligne et se merge seul sur CI verte change la consigne de tous les suivants sans relecture (ADR-053, PR #482).
**Alternative rejetée** : une interface d'acceptation — un déplacement de texte suffit.

## ADR-056 — Un run travaille dans son worktree

**Date** : 2026-10-19
**Décision** : un projet `tracked` qui déclare `worktree` dans `agents.json` exécute chaque run dans `<IDE_WORKTREES_DIR>/<projet>/<ticket>`, créé depuis `origin/<base>` avec `core.longpaths`. Ce dossier est la racine d'écriture (amende ADR-031) ; `git_root: ancestor` désigne le dépôt dont il est le worktree (amende ADR-028). `populate` copie ce qui s'édite, lie le reste s'il est ignoré par git, jamais le `.env` de Tessera. Un lien se retire avant toute suppression récursive. Le dossier disparaît au commit final, sauf travail non commité ; au démarrage, un orphelin se commite (ADR-037) puis disparaît. `RunLock` reste, base partagée (ADR-051) : "même arbre" (ADR-038) devient "même base".
**Raison** : le 16/10 un run a sali le checkout d'une session et commité un ticket écrit à la main (#508) ; le 14/10 une jonction a vidé `node_modules`.
**Alternative rejetée** : des gardes sur le checkout partagé — le partage nuit.
**Détail** : `docs/superpowers/specs/2026-10-19-worktree-par-run-design.md`

---

## ADR-057 — La doc par lot se lit dans le code livré

**Date** : 2026-10-23
**Portée** : architect, codeur
**Décision** : amende ADR-035. `doc-technique` et `doc-fonctionnelle` reçoivent, en plus des tickets, le diff livré de chaque ticket (borné) et le contenu des fichiers qu'il touche. Chaque édition cite un extrait de ce code, recopié ; les nombres, ADR et noms qu'elle introduit doivent y figurer, sinon elle est refusée. Le lot tient en 5 tickets, les plus anciens d'abord ; un ticket sans diff retrouvable n'est pas documenté, et le journal le dit. Une édition ne réécrit qu'un volume borné. Le modèle par défaut des deux rôles est Sonnet.
**Raison** : le 22/10, Haiku a deviné noms, numéros et chiffres que seul le code porte ; deux lots ont été jetés.
**Alternative rejetée** : un outil `Read` — ces rôles n'ont pas d'outils, et un modèle qui explore coûte sans rien prouver.
**Détail** : `docs/superpowers/specs/2026-10-23-documentation-depuis-le-code-design.md`

---

## ADR-058 — Le Bureau remplace Supervision, et rien n'y est décoratif

**Date** : 2026-10-23
**Décision** : la vue Bureau devient la vue par défaut de Supervision ; elle garde toutes ses fonctions (cartes, fil, rangement, services) et la vue Liste reste dans le sélecteur. Chaque sprite, objet ou bulle rend un état réel que le store de run ou l'API fournit déjà ; sans donnée, rien n'est dessiné, sauf le mobilier d'une salle, fixe et sans voyant (ticket-583). Les sprites sont des SVG inline en pixels, sous `design/bureau/`, animés par `transform` et `opacity`, coupés par `prefers-reduced-motion`.
**Raison** : la Liste reste nécessaire au clavier et au lecteur d'écran ; un décor qui ment sur l'état ruine la confiance dans la vue.
**Alternative rejetée** : canvas — il ne se teste pas avec Testing Library et un lecteur d'écran ne le lit pas.
**Détail** : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md`

---

## ADR-059 — Un run « rapide » prend le repli d'emblée

**Date** : 2026-10-27
**Décision** : complète ADR-046. À côté de l'indisponibilité, un second déclencheur du repli : le choix explicite, au lancement (`rapide` dans `RunRequest`, faux par défaut). Un rôle qui déclare un `fallback` est alors construit directement avec lui, sans principal, et chaque appel porte le modèle du repli. Un rôle sans repli ne change pas. Le choix s'écrit une fois par run dans `memory/pipeline-log.md`. Une réponse illisible ne déclenche toujours aucun repli.
**Raison** : sur ce PC, le validateur local prend environ 5 min 30 par ticket contre environ 1 min sur Haiku. Ollama reste le premier choix, Haiku quand on est pressé.
**Alternative rejetée** : changer le défaut des `agents.json` — le réglage par défaut économise le quota.

---

## ADR-061 — Un verdict de rôle se rend en JSON validé par un schéma

**Date** : 2026-10-27
**Décision** : reviewer, sécurité et validateur rendent leur verdict dans une sortie structurée que le provider valide : `output_format` du SDK, `format` d'Ollama, outil forcé de l'API Anthropic. `ProviderResult.structured` la porte ; le repli reçoit le même schéma. Une sortie absente, hors schéma ou contradictoire refuse (`CHANGES_REQUESTED` / `BLOCK`), sans relecture du texte par mot-clé. Le reviewer rend `verdict`, `summary` et `blocking[{text, location, confidence}]` : le seuil du ticket-574 s'applique au champ, et `APPROVED` avec une remarque au-dessus du seuil refuse. ADR-009 est amendée à la livraison du reviewer.
**Raison** : le texte libre a coûté trois tickets de rustines (122, 298, 574) ; un champ typé remplace une regex.
**Alternative rejetée** : garder le mot-clé en repli d'un JSON invalide — une réponse ambiguë approuverait, ce que l'échec fermé interdit.

---

## ADR-062 — Le contrôle visuel d'un run se déclare, se joint au run et ne juge pas

**Date** : 2026-10-27
**Décision** : un projet déclare `pipeline.controle_visuel` (`joindre` ou `relire` ; absent, rien ne tourne) et, dans `captures`, ses fichiers d'interface et le démarrage de l'app. Si le diff approuvé touche l'interface, Tessera lance l'app depuis le worktree (ADR-056) sur un port libre, capture hors du dépôt (ADR-021), l'arrête et joint les images au run, pas à la PR. Aucun modèle ne les juge. `joindre` : un échec se journalise. `relire` : la PR ne se merge jamais seule (ADR-033), échec de capture compris (ADR-039).
**Raison** : le 23/10 un chevauchement entre 1024 et 1150 px a passé reviewer et validateur, qui lisent un diff.
**Mesure** : non faite ; borne haute 7 min par run, durée réelle journalisée (ticket-618).
**Alternative rejetée** : un validateur à vision — le contrat de chaque provider à étendre.

---

## ADR-064 — Un agent de produit se dessine depuis un fichier d'activité

**Date** : 2026-10-29
**Décision** : complète ADR-058. « En cours » devient une salle par app lancée, qui montre d'abord l'état connu (`AppEnCours`, `ServiceActif`). Un agent n'y est dessiné que si `services[]` de `agents.json` déclare `activite`, chemin d'un JSON que le produit écrit et que Tessera lit. Fichier absent, périmé, hors schéma, hors du projet, ou service arrêté : personne n'est dessiné (ADR-039).
**Raison** : zéro token, valable pour une app lancée à la main, aucune route à interroger.
**Mesure** : non faite ; aucun produit n'émet encore.
**Alternative rejetée** : route de santé enrichie (app arrêtée muette, contrat HTTP par produit) ; sortie du service (seules les apps lancées par Tessera, texte à parser).
**Détail** : `docs/superpowers/specs/2026-10-29-salle-des-serveurs-design.md`

---

## ADR-065 — La livraison d'un ticket attend le merge des PR déjà confiées au watcher

**Date** : 2026-10-29
**Décision** : complète ADR-051. Avant son rebase, la phase 1 attend que les autres tickets du projet tenus par `CIWatcher` aient fini, mergés ou bloqués. Attente bornée (1 500 s) ; passé le délai, la livraison part comme avant. Aucun push forcé : la tête poussée reste celle que le reviewer a lue.
**Raison** : une PR de file est devenue conflictuelle sur la documentation quand sa voisine a été mergée après coup. Rebaser après ce merge supprime la cause (ADR-022, ADR-039).
**Mesure** : non faite ; coût : un ticket prêt attend la CI du précédent.
**Alternative rejetée** : push forcé depuis le watcher (`pushed_sha` périmé) ; `merge=union` côté dépôt (GitHub l'ignore) ; partir de la branche du précédent (défait ADR-056).
**Limite** : une PR rendue conflictuelle hors file reste arrêtée sur « à rebaser » (ticket-674).

---

## ADR-067 — Le garde git et gh n'admet que des lectures nommées

**Date** : 2026-10-30
**Décision** : amende ADR-027. Le hook refuse toute sous-commande `git` ou `gh` absente d'une liste blanche de lectures (`status`, `diff`, `log`, `show`, `gh auth status`…). Les options globales (`-c`, `--repo`, `-R`) se lisent avant la sous-commande ; `-c` n'accepte que des clés cosmétiques ; `--output` est refusé. Une assignation ou un mot-clé de shell en tête de segment se saute ; `cmd` et `powershell` sont des shells.
**Raison** : la liste noire laisse passer des formes naturelles — `<VAR>=<valeur> git push`, `gh --repo <o/r> pr merge`, `git bisect run`. Un faux refus se corrige d'une ligne ; un faux passage est un push (ADR-022).
**Alternative rejetée** : allonger la liste noire — chaque trou comblé en révèle un autre ; analyser le shell en entier — hors de portée, ADR-027 le dit déjà.

---

## ADR-068 — Le service de documentation n'écrit dans `agents.json` que la clé `description`

**Date** : 2026-10-30
**Portée** : doc-technique
**Décision** : précise ADR-027. Aucun agent n'écrit `agents.json`. doc-technique propose une `description` (220 caractères, une ligne, avec `preuve`) dans sa sortie ; le service la contrôle comme toute édition (ADR-057) et ne remplace que cette clé, par substitution de texte : le reste du fichier reste octet pour octet. Un refus est journalisé et ne bloque pas le lot. L'écriture vise la copie du run, jamais le checkout (ADR-056). `AGENTS.md` suit `CLAUDE.md` (`doc_claude_md`).
**Raison** : les descriptions affichées dataient de la création des projets, et un humain relisait 17 projets à la main.
**Alternative rejetée** : donner `agents.json` à l'agent (ADR-027) ; réécrire le fichier par `json.dumps` — il reformaterait tout.

---

## ADR-069 — Une PR conflictuelle se met à jour par un merge, sans push forcé

**Date** : 2026-11-02
**Décision** : complète ADR-065. Sur une PR `conflicting`, le watcher fusionne `origin/<base>` dans la tête poussée, puis pousse sans forcer. Il n'agit que si la tête de la PR est encore `pushed_sha`, et n'admet que des conflits de journaux résolus en union ; aucun agent n'écrit ici. Les tests rejouent avant le push, `pushed_sha` prend la nouvelle tête avant l'attente de la CI, puis le merge reste automatique.
**Raison** : même règle qu'au rebase de phase 1 : une résolution par règle se merge sur CI verte, celle d'un agent se relit (ADR-033). L'approbation suit la lignée des têtes, jamais une tête étrangère (ADR-039).
**Alternative rejetée** : `update-branch` de GitHub — il refuse un conflit, le cas visé ; rebase puis push forcé (ADR-022) ; ne rien faire — l'arrêt actuel (ticket-452).
**Détail** : tickets 732 et 733.

---

## ADR-070 — Les sprites du Bureau se dessinent avec le moteur, en symboles partagés

**Date** : 2026-11-03
**Décision** : complète ADR-058. Un sprite est une grille de jetons `famille.ton` calculée par le moteur de l'atelier (`lib/bureau/sprites/`), colorée par les variables `--sprite-*` de `sprites-theme.css`, redéfinies la nuit. Chaque calque devient un `<symbol>` adressé par son contenu dans un `<defs>` commun ; une instance n'est qu'un `<use>`, qui lie peau, cheveux et haut. Sol et murs sont des `<pattern>`. Le cosmétique sans état (reflets, étoiles, marche) est permis ; un état reste soumis à ADR-058, en jetons `etat-*` fixes jour et nuit, jamais contourés (ADR-026).
**Raison** : un `<path>` par jeton portait dix pièces à 3 974 nœuds SVG pour un plafond de 2 250 ; partagées, elles en font 1 815.
**Alternative rejetée** : relever le plafond — la vue se relit toutes les 10 s ; un canvas — ADR-058.
**Détail** : ticket-727.

---

## ADR-071 — Un prompt trop gros pour un provider local part directement sur son repli

**Date** : 2026-11-03
**Décision** : amende ADR-046. Un rôle dont le principal est `ollama` et qui déclare un `fallback` peut déclarer `fallback_above_chars` : au-delà de cette taille de prompt, l'appel part sur le repli sans tenter le principal. C'est un troisième déclencheur, à côté de l'indisponibilité et du run `rapide` ; une réponse illisible n'en déclenche toujours aucun.
**Raison** : un modèle local tronque ou refuse un prompt plus long que sa fenêtre, et le constat n'arrive qu'après un appel long et inutile ; la taille se connaît avant l'appel.
**Alternative rejetée** : tronquer le prompt — le validateur jugerait des critères qu'il n'a pas lus ; router selon la taille du ticket (écarté par ADR-046) — la taille du prompt est le vrai critère, et seulement pour un local.
**Détail** : ticket-714 ; relevé par l'audit du 30/10.

---

## ADR-072 — La porte de configuration des tests connaît tous les fichiers et veut un chemin complet

**Date** : 2026-11-03
**Décision** : complète ADR-027. La liste des fichiers de configuration des tests s'étend à `pytest.ini`, `tox.ini`, `setup.cfg`, `mypy.ini`, `.mypy.ini`, `.coveragerc`, `vite.config.*` et `vitest.workspace.*`. Un fichier touché n'est couvert par le ticket que si son chemin complet depuis la racine du dépôt y figure ; le nom de base ne suffit plus.
**Raison** : `pytest.ini` et `mypy.ini` priment sur `pyproject.toml`, et la configuration vitest de ce dépôt vit dans le bloc `test:` de `vite.config.ts` : la porte était inerte sur eux. Un ticket qui citait `frontend/src/x/vitest.config.ts` couvrait aussi `frontend/vitest.config.ts`.
**Alternative rejetée** : lire le bloc `test:` de `vite.config.ts` seul — plus fin, mais un changement ailleurs dans ce fichier (alias, plugins) peut aussi désarmer les tests ; le ticket n'a qu'à le nommer.
**Détail** : ticket-748 ; relevé par l'audit du 30/10.

---

## ADR-073 — Les secrets de Tessera vivent dans le coffre du système

**Date** : 2026-11-05
**Décision** : complète ADR-053. Neuf secrets (`ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, les cinq jetons de mise en ligne, `STATIC_TOKEN`, `FORBIDDEN_TERMS`) vont dans le coffre du système, via `keyring`. Lecture : variable d'environnement, coffre, puis `.env`. `SECRETS_SOURCE=auto` par défaut (05/11, multi-PC) : sans coffre, `.env` et avertissement, refus si un secret migré manque ; un PC migré passe en `coffre` ; `env` pour CI et Docker. Un secret ne s'exporte jamais dans un sous-processus. Le hook `pre-push` lit par le backend et refuse s'il ne peut pas lire. Le garde d'ADR-053 refuse aussi les commandes qui exécutent le coffre.
**Raison** : `.env` se lit, se copie et se synchronise ; le coffre chiffre au repos. Tout processus de l'utilisateur le lit pourtant : le plafond d'un jeton reste sa portée.
**Alternative rejetée** : chiffrer `.env` — la clé de déchiffrement reste à côté.
**Détail** : `docs/superpowers/specs/2026-11-05-secrets-dans-le-coffre-design.md`.

---

## ADR-074 — Les leçons d'un projet vivent dans `memory/lecons.md`

**Date** : 2026-11-05
**Décision** : après un run approuvé dont `review_feedback` n'est pas vide, le service, sans outils, écrit au plus une leçon « Quand <situation>, <action>. » sous `## Proposées` de `memory/lecons.md`, artefact d'ADR-021 et ADR-023. Un humain la déplace sous `## En vigueur`, seule section injectée, au codeur et au reviewer, sous les contraintes : 25 leçons, 4 Ko. Refus : hors forme, 200 caractères, preuve absente du retour, doublon, vérification affaiblie. Un diff de run qui touche ce fichier met le run en `blocked` (ADR-055). Une leçon dit un piège observé ; `decisions.md` dit un choix.
**Raison** : ticket-736 a perdu trois tours sur des doubles de test ; un texte de modèle injecté sans relecture change la consigne de tous (ADR-055).
**Alternative rejetée** : écriture directe par l'agent, ou activation automatique — la confiance accordée à un texte non relu est une décision humaine.

---

## ADR-075 — Cinq réglages modifiables depuis l'interface, figés par run

**Date** : 2026-11-05
**Décision** : `run_max_budget_usd`, `llm_max_budget_usd`, `dialogue_timeout_s`, `max_parallel_test_runs` et `keep_awake_during_runs` se modifient depuis l'interface, dans un registre fermé et borné ; « sans plafond » ne se pose que dans `.env`. Secrets (ADR-073), chemins, hôtes et réglages par projet n'y entrent jamais. La valeur vit en SQLite au-dessus du défaut de `.env`, que rien ne réécrit ; `reglages.courants()` est l'unique lecture. Un run fige plafonds et délai à l'ouverture ; les deux réglages de machine valent à leur prochaine lecture. Une écriture exige un `Origin` déclaré (ticket-754), sinon 403.
**Raison** : l'API est ouverte quand `STATIC_TOKEN` est vide et un agent a `Bash` : ni lui ni une page locale ne doivent relever un plafond.
**Alternative rejetée** : réécrire `.env` — le redémarrage coupe les runs ; appliquer à chaud — un plafond bougerait sous un run.
**Détail** : `docs/superpowers/specs/2026-11-05-reglages-globaux-design.md`.

---

## ADR-076 — Ranger `services/` par domaine, sans import vers un rang plus haut

**Date** : 2026-11-05
**Décision** : `services/` se range en dix-huit domaines, du plus bas au plus haut : noyau, projets, usage, provisioning, gardes, git_workspace, worktrees, github, providers, verification, verdicts, agents, documentation, creation_projet, livraison, pipeline, file, supervision. Un module n'importe que son domaine ou un plus bas ; `test_sens_des_imports.py` le mesure, avec cliquet. `tessera/agents/` disparaît : `github_sync` rejoint `github`. Ordre : `ORDRE` de `test_domaines_services.py`. Les déplacements gardent le comportement, un domaine par ticket, chacun attendant le merge du précédent.
**Raison** : deux cents modules à plat ne disent ni où chercher ni qui importe qui ; `agents/` échappait au contrôle.
**Alternative rejetée** : tout déplacer d'un coup — conflit avec chaque PR ouverte ; une façade à l'ancien chemin — les `monkeypatch` par chaîne cessent de s'appliquer, sans erreur.

---

## ADR-078 — Un détecteur d'anomalies observe les runs sans les arrêter

**Date** : 2026-11-05
**Décision** : une tâche de fond du backend relit toutes les 5 min, en lecture seule, chaque run vivant. Six règles : outil répété 4 fois, étape ou coût au-delà de 3 × la médiane du projet, 15 min sans événement, dernier tour de revue, deux blocages de même cause. Chaque anomalie se signale une fois, en `run_anomaly` : cloche, Bureau, salle Tessera, historique, log. Elle n'arrête, ne relance ni ne modifie aucun run.
**Raison** : le 03/11, testeur figé de 19 h à 7 h 48, trois tours perdus sur des doubles de test, deux livraisons coupées par le réseau : seul un humain l'a vu ; « figé ? » ignore les étapes silencieuses.
**Alternative rejetée** : couper au seuil — un faux positif perd un travail payé (ADR-037).
**Détail** : spec 2026-11-05-detecteur-d-anomalies-design.md, tickets 794 à 833.

---

## ADR-080 — Un superviseur agit par actions fermées, dans des bornes déclarées

**Date** : 2026-11-05
**Décision** : `superviseur`, sans outil, choisit parmi quatre actions : trier un signalement, décider une leçon ou règle déléguée, reconfier une PR verte à `CIWatcher`, relancer une file coupée par l'infrastructure. Le code les exécute, une par commit, sous `RunLock`, jamais pendant une file. Jamais : argent, suppression, secrets, projet `professional`, `agents.json`, `.github/`, `CLAUDE.md`, règle qui le borne. Délégation déclarée dans `agents.json`, sinon rien (amende ADR-055, ADR-074). Tout agent outillé a `signaler`, borné ; la revue de projet est un run `design` sans code. Un numéro rendu est pris.
**Raison** : le 05/11, ADR-074 et tickets 801-804 renumérotés après coup, file coupée sur « ticket-847 introuvable », PR #913 sans surveillance.
**Alternative rejetée** : un agent avec `Bash` — rien ne borne ses effets.
**Détail** : spec 2026-11-05-superviseur-design.md.

---
