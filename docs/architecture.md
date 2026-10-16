# Architecture — Tessera

## Vue d'ensemble

```
┌─────────────────────────────────────────┐
│       ✅ Tauri v2 Shell (Rust)          │   ← ticket-010
│  ┌───────────────────────────────────┐  │
│  │   ✅ React UI (TypeScript)        │  │   ← tickets 007-014
│  │  Monaco Editor (local bundle)     │  │
│  │  Ticket Board · Agent Stream      │  │
│  │  Sidebar (projets + tickets)      │  │
│  │  CreateProjectModal               │  │
│  └──────────────┬────────────────────┘  │
└─────────────────┼───────────────────────┘
                  │ HTTP + WebSocket
┌─────────────────▼───────────────────────┐
│       Orchestrateur (FastAPI Python)    │   ← ✅ implémenté
│                                         │
│  Routers                Services        │
│  ├─ /projects      ├─ ProjectLoader     │
│  ├─ /tickets       ├─ TicketService     │
│  ├─ /agents        ├─ AgentRunner       │
│  └─ /orchestrator  ├─ Orchestrator      │
│                    ├─ ProjectCreator    │
│                    ├─ GitHubService     │
│                    ├─ GithubSyncAgent   │
│                    ├─ GitWorkspaceSvc   │
│                    └─ DatabaseService   │
│                           │             │
│              LLMProvider (ADR-017)      │
│      ┌────────────────┴──────────────┐  │
│  ClaudeAgentSDKProvider     AnthropicApi│
│  (défaut — abonnement,      Provider    │
│   outils fichier)           (fallback)  │
└─────────────────────────────────────────┘
                  │
       Filesystem (tickets Markdown + mémoire)
                  │
       git (une branche + un commit par run — ADR-018)
                  │
       SQLite  tessera.db  (historique pipelines)
```

### Couche LLM (ADR-017)

Les services n'appellent jamais Claude directement : ils passent par le protocole
`LLMProvider` (`complete` / `stream`). Deux implémentations coexistent —
`ClaudeAgentSDKProvider` (défaut, facturé sur l'**abonnement**, dispose des outils
fichier) et `AnthropicApiProvider` (fallback sur crédits API, pour les
environnements sans session interactive : Docker, CI).

`get_provider(allow_tools=False)` retourne une variante **sans outils**, utilisée
par tous les services purement texte→JSON (validateur, auditeur sécurité,
planificateur, project-analyzer, agent-creator, project-creator, doc-technique,
doc-fonctionnelle) qui
écrivent eux-mêmes leurs fichiers en Python.

### Isolation du contexte CLAUDE.md pour les projets hébergés

Les projets situés sous `projects/` ne doivent lire que leurs propres consignes dans `CLAUDE.md`, pas celles de Tessera. Seul le projet bootstrap `projects/ide-core/` — qui définit l'IDE lui-même — hérite du `CLAUDE.md` racine et de ses dépendances (`@`-imports).

Lors de la création des `ClaudeAgentOptions` (fournisseur Agent SDK), le service exclut les CLAUDE.md ancêtres pour tout projet hébergé qui n'est pas un projet `ancestor`. L'exclusion est posée via le paramètre `claudeMdExcludes` (liste de chemins) dans les `settings` de l'agent. Cette isolation évite que les consignes système — `STATIC_TOKEN`, termes interdits, limites de budget — contaminent le contexte d'un projet autonome ayant ses propres règles.

### Shell des agents (Windows — ticket-319)

Sous Windows, Claude Code n'active `Bash` que s'il trouve Git Bash à un emplacement standard.
Git installé par un gestionnaire comme `scoop` échappe à cette détection automatique, ce qui
laissait les agents sans shell bien que le CLAUDE.md le promette.

L'IDE résout ceci au démarrage :
- Si `CLAUDE_CODE_GIT_BASH_PATH` est posée, elle est utilisée.
- Sinon, l'IDE cherche `git` via `shutil.which()` et place `bash.exe` au même endroit.
- Pas trouvé : l'IDE continue, mais `GET /health` rend `"agent_shell": false`, avertissant que
  les outils shell vont manquer.

Chaque appel d'agent SDK reçoit `CLAUDE_CODE_GIT_BASH_PATH` dans son environnement, permettant
au Code Engine local de lancer Bash. Hors Windows, ce mécanisme ne s'applique pas (bash est
toujours disponible) et `agent_shell` vaut `true`.

### Enregistrement automatique des appels

Chaque appel LLM d'un run est enregistré dans `agent_calls` avec `run_id`,
`ticket_id`, `role`, `model` et le **provider qui a effectivement répondu**, par
deux chemins qui ne se recouvrent pas :

- le codeur et le reviewer passent par `AgentRunner`, qui enregistre lui-même ;
- la sécurité, le validateur et la documentation appellent leur provider
  directement : `ProviderEnregistrant` enveloppe ce provider et enregistre à
  leur place, sans que le service le sache.

Si un rôle est déclaré sur Ollama mais que le serveur est indisponible, le
provider enregistré est "agent_sdk" (Claude), avec le modèle du repli et son
coût réel. Ollama tourne à coût nul : un appel Ollama enregistre `cost_usd = 0.0`
(ADR-046).

Les appels hors run — chat, analyse de projet — n'ont pas de `run_id` et ne
sont pas écrits dans `agent_calls` : ils ne peuvent donc jamais se mélanger aux
appels d'un pipeline.


### Logs du backend (ticket-330)

Au démarrage, le backend configure un logger qui écrit dans un fichier rotatif `backend/logs/tessera.log`, en plus de la sortie standard. Cela garantit qu'une trace persiste après un crash.

**Garanties** :
- Le dossier `backend/logs/` est créé s'il n'existe pas
- Les fichiers tournent (rotation basée sur la taille)
- Les exceptions non rattrapées dans les tâches `asyncio` y sont capturées avec leur trace complète
- Les fichiers `.log` sont ignorés par git

Un opérateur peut consulter ces fichiers pour déboguer un arrêt inattendu du backend.


### Gestion du parallélisme des tests (ticket-348)

Quand plusieurs files tournent en parallèle sur plusieurs projets, le testeur de 
chaque file lançait simultanément sa suite complète. Cela saturait la machine — 
six suites d'environ six minutes chacune ne laissaient à aucune de CPU libre, 
causant des timeouts (ticket-347).

`TestRunnerService` est instancié à chaque requête. Un verrou posé sur l'instance 
ne protège rien. La solution est un `asyncio.Semaphore` **au niveau du module**, 
créé paresseusement à la première utilisation avec la valeur `max_parallel_test_runs` 
(défaut **2** — configuré dans `config.py`, variable `MAX_PARALLEL_TEST_RUNS`).

**Garanties** :
- Au maximum `N` suites de tests tournent en parallèle sur la machine, tous 
  projets confondus
- Le timeout ne s'écoule qu'**après** l'obtention du créneau — l'attente en file 
  d'attente n'est pas décomptée du délai alloué
- Un rappel optionnel `en_attente: Callable` est appelé une seule fois quand un 
  créneau n'est pas immédiatement disponible, permettant au pipeline d'enregistrer 
  une ligne dans le log : `[ticket-XXX] testeur: en attente d'un créneau de test`
- Le créneau est rendu sur tous les chemins de sortie : timeout, exception, 
  annulation (`async with`)

Un réglage à 0 ou moins **désactive** cette borne — utile pour le développement 
mono-projet ou les machines puissantes. La valeur par défaut de 2 est 
suffisante pour une machine de développement typique sous quatre cœurs.

#### Parallélisme des chaînes frontend et backend (ticket-351)

`verifier.py` organise les tests en deux chaînes indépendantes, exécutées en parallèle :

- **BACKEND_STEPS** : pytest (tests), puis mypy (type-checking)
- **FRONTEND_STEPS** : tsc (type-checking), eslint (linter), puis vitest (tests)

Chaque chaîne s'exécute séquentiellement — un échec dans une étape bloque les suivantes de la même chaîne — et s'arrête à son premier échec. Les deux chaînes tournent simultanément, ce qui réduit la durée totale au maximum des deux au lieu de leur somme. Le code de sortie est non nul si l'une des deux échoue. Les sorties sont capturées séparément pour éviter l'entrelacement et affichées à la fin : d'abord backend, puis frontend.

### Gestion du parallélisme Ollama (ticket-350)

Quand plusieurs runs utilisent un même serveur Ollama local, les requêtes
se disputaient le modèle et la mémoire. Un validateur appelant le même serveur
qu'un codeur voyait ses délais grandir — des validations de 330 secondes ont
été relevées le 2026-10-05, frôlant le timeout de 300 s. Quand le délai de
lecture httpx commence à courir en attente invisible du créneau du serveur,
l'appel expire sans avoir pu faire de progrès.

`OllamaProvider` est instancié par rôle (`provider_pour_role`) : un verrou sur
l'instance ne protège qu'elle seule. Plusieurs rôles demandent le même modèle
à la fois. La solution est un `asyncio.Semaphore` **au niveau du module**,
créé paresseusement à la première utilisation, keyed par la `base_url` du
serveur, avec la valeur `OLLAMA_MAX_CONCURRENT` (défaut **1** — configuré dans
`config.py`).

**Garanties** :
- Au maximum **1** requête en vol par `base_url` à la fois
- Plusieurs serveurs Ollama (différentes `base_url`) ne se bloquent pas
  mutuellement
- L'attente du créneau n'est pas bornée par le timeout httpx : le délai de
  lecture ne s'écoule qu'après l'envoi réel de la requête
- Un flux (`stream`) abandonné avant sa fin rend le créneau : un `complete`
  suivant aboutit
- Une requête en erreur rend le créneau, exception quelconque

Un réglage à 0 ou moins **désactive** cette limite — toutes les requêtes sont
lancées concurremment. Utile pour déboguer un modèle ou tester le
load-balancing interne d'Ollama.

La sérialisation des requêtes (une par serveur) évite la compétition pour le modèle
et la mémoire. Un serveur saturé ou trop lent bascule rapidement sur le repli :

- **Attente de créneau bornée** : si une requête attend un créneau plus de
  `OLLAMA_SLOT_WAIT_S` secondes (défaut 30), elle lève `ProviderIndisponible`
  et le repli prend le relais, sans dépenser le temps d'attente.
- **Disjoncteur par serveur** : après un dépassement du délai de lecture, ce
  serveur est marqué lent pendant `OLLAMA_COOLDOWN_S` secondes (défaut 600) ;
  pendant cette période, tout appel lève `ProviderIndisponible` aussitôt,
  sans requête HTTP. L'appel suivant, s'il arrive après le refroidissement,
  envoie une nouvelle requête.
- **Message clair** : un dépassement du délai produit « Ollama : délai
  dépassé (… s) », distinct d'une connexion refusée.

Voir [configuration](configuration.md#ollama) pour les réglages.

### Parsing et caching off-loop (ticket-352)

`TicketService.list_tickets()` et `ProjectLoader.list_projects()` relisaient chaque fichier à chaque requête, bloquant la boucle d'événements sur du parsing YAML. Problème : le pipeline appelle ces services plusieurs fois par étape; avec plusieurs files, l'interface gelait.

**Optimisation** : cache de parsing par fichier, clé `(chemin résolu, st_mtime_ns, st_size)`. Chaque requête fait un `stat()` peu coûteux; seul un fichier modifié est re-parsé. Même logique pour projets (`CLAUDE.md`, `agents.json`). Tout travail disque via `asyncio.to_thread` — la boucle n'est jamais bloquée.

Invariant : deux requêtes successives sans changement de fichier ne lisent et ne parsent chacun qu'une fois.

### Couche git (ADR-018, ADR-024, ADR-027)

`GitWorkspaceService` isole les opérations git du pipeline, et ne s'applique
**jamais** au dépôt de Tessera lui-même — uniquement au projet ciblé.

Cette promesse a demandé douze correctifs, tous nés d'un usage réel :

- **Le projet doit être la racine de son dépôt** (ADR-024). `git rev-parse
  --is-inside-work-tree` réussit aussi quand le dépôt trouvé est un *ancêtre* :
  un dossier posé dans `projects/` sans dépôt propre faisait remonter git
  jusqu'à celui de Tessera, où le run créait sa branche et son commit. La
  vérification compare désormais `--show-toplevel` au dossier du projet.
- **Les agents ne font pas de git** (ADR-027). Contraindre cette classe ne
  contraignait qu'elle : le codeur a `Bash` et pouvait lancer `git commit`,
  `git merge`, `git push` sans passer par elle — ce qu'il a fait, jusqu'à
  pousser sur `main`. Un hook `PreToolUse` refuse maintenant toute
  sous-commande git qui écrit. Le git en lecture reste permis.
- **Les lockfiles sont résumés dans le diff relu** (ticket-272). Quand un run
  modifie un fichier de verrouillage connu — `uv.lock`, `package-lock.json`,
  `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Cargo.lock` — le diff relu ne
  porte qu'une ligne de résumé : `<chemin> : fichier de verrouillage modifié,
  N lignes ajoutées, M supprimées`. Cela évite que des milliers de lignes noient
  les changements réels du ticket. Le commit, lui, porte le lockfile en entier.
- **Artefacts dans le matériau relu** (ticket-274). Les fichiers de mémoire 
  et de tickets — `memory/decisions.md`, `tickets/todo/`, etc. — ne sont ni 
  versionnés (mode `artifacts: local`) ni inclus au diff relu standard 
  (mode `artifacts: tracked`). Or, un ticket de cadrage crée justement des 
  décisions et des tickets qui doivent être jugés par le reviewer et le 
  validateur. Le pipeline transmet désormais ces artefacts au matériau relu, 
  sans les committer.
- **Fichiers vidés détectés et signalés** (ticket-277). Si le codeur vide un
  fichier suivi au lieu de le supprimer (par oubli du `rm`), le pipeline
  signale le fichier vidé dans le rapport du run — un événement ou une ligne de
  log lisible à l'écran — sans bloquer le commit. Seul un fichier suivi
  **ramené à vide** est signalé ; un fichier vide créé initialement ne l'est
  pas. Cette détection aide à repérer les suppressions mal faites avant qu'elles
  n'échouent en CI.
- **Le journal du pipeline n'arrête plus le ticket suivant** (ticket-278). 
  `ensure_clean_tree` ignore les fichiers que le pipeline écrit et commite 
  lui-même : `memory/pipeline-log.md` et les fichiers de `tickets/`. Une 
  modification ailleurs reste un refus. Cette liste vit à un seul endroit, 
  partagée avec ce que le diff relu exclut déjà.
- **Les fichiers de configuration ne sont jamais commités** (ticket-296). 
  Les réglages faits dans l'IDE pendant un run — `agents.json`, 
  `.claude/settings*.json`, `.github/workflows/` — ne doivent pas partir 
  dans le commit du pipeline. Le commit les exclut par pathspec, et l'arbre 
  les garde modifiés : le rapport du run signale lesquels ont changé. Cela 
  prévient qu'un réglage d'IDE voyage dans la PR d'un ticket qui ne l'avait 
  pas demandé (incident du ticket-279).
- **Commit des artefacts de tenue de livres avant la création de branche du ticket
  suivant** (ticket-314). Avant de créer la branche d'un nouveau ticket, 
  le pipeline commite les fichiers modifiés par les étapes précédentes
  (`memory/pipeline-log.md` et fichiers de `tickets/`) via `commit_bookkeeping`. 
  Cela évite que ces fichiers bloquent le `git checkout -b` du ticket suivant. 
  Si ce commit échoue (absence de configuration git, pas de HEAD), le pipeline 
  tente quand même le checkout ; seul un fichier de code modifié déclenche 
  un `blocked` avec un `GitCommandError` explicite.
- **Messages d'erreur d'arbre sale nomment les fichiers qui bloquent** (ticket-323). 
  Quand l'arbre de travail contient des modifications en dehors de la tenue de 
  livres au démarrage du run, l'événement `error` porte la liste des fichiers 
  suivis qui ont changé. Le Pipeline log et la vue du run affichent ces chemins, 
  permettant à l'utilisateur de savoir immédiatement ce qu'il faut commiter ou 
  annuler avant de relancer le pipeline.
- **Branche existante rejouée sur la base actuelle** (ticket-329). Quand un 
  ticket est relancé, sa branche locale peut exister mais être basée sur une 
  version antérieure de la branche de base. Le pipeline détecte ce cas et 
  rejoue la branche sur la base actuelle via `git rebase`. Si le rejeu crée 
  des conflits, l'ancienne branche est renommée en `stale/ticket-XXX` pour 
  préservation, et une nouvelle branche est créée depuis la base actuelle. 
  Cela évite qu'un ticket relancé reprenne silencieusement du travail périmé.
- **Recherche du ticket dans tous les dossiers de statut** (ticket-329). Si 
  le fichier ticket n'existe pas dans le dossier attendu — par exemple, un 
  run interrompu a déplacé le ticket dans `tickets/blocked/` sans le committer 
  — le pipeline le cherche dans tous les dossiers (`todo/`, `in-progress/`, 
  `in-review/`, `done/`, `blocked/`, `archive/`). Si absent localement, il 
  le cherche sur la branche de base distante. Seul si absent partout, le 
  pipeline émet un événement d'erreur et passe le ticket en `blocked`.
- **Chemins accentués lus correctement** (ticket-346). `git ls-files` et autres 
  commandes listant les chemins encodent les noms non ASCII avec guillemets et 
  octets échappés — `"tickets/todo/ticket-004-clavier-fl\303\250ches.md"` — ce qui 
  ne correspond à aucun chemin réel du système de fichiers. Toute lecture de liste 
  de chemins git utilise désormais l'option `-z` (séparateur null) ou 
  `-c core.quotePath=false` (désactiver l'échappement), et découpe sur le 
  séparateur réel. Cela garantit que les tickets à accent ne sont jamais perdus 
  lors du balayage des modifications ou du déplacement de fichiers.

Un run dont le commit **échoue** ne peut pas s'annoncer approuvé : le ticket
passe `blocked` et la raison est émise. « Rien à committer » reste un succès, et
s'en distingue.

#### Préservation des fichiers suivis lors de l'exclusion en mode local (ticket-446)

Le mode `local` pour les artefacts écrit les règles d'exclusion dans `.git/info/exclude` (ADR-021, ADR-023). Avant de commiter, la purge des fichiers stagés mais ignorés (`_purger_stage_ignoré` dans `git_workspace.py`) s'est compliquée : elle vérifie maintenant qu'un fichier n'existe pas dans `HEAD` avant de le retirer de l'index. Un fichier suivi par le dépôt initial reste suivi, même s'il est marqué ignoré après coup. Sur un dépôt sans commit (`HEAD` absent), la purge agit comme avant.

### Reprise de runs orphelins (ticket-369)

Au démarrage du backend, après la solidification des runs orphelins en base (`solder_les_runs_orphelins`, ticket-177), une étape remet les dépôts en état quand un arrêt les a laissés sales pendant un run.

Pour chaque run interrompu, si la copie de travail du projet est restée sur une branche `<ticket_id>-…` :

1. Les changements non committés sont committés avec le message du pipeline non approuvé, ce qui garantit que l'arbre n'est jamais sale entre deux runs (ADR-018)
2. La fiche de ticket est remise en `todo` si elle était en `in-progress` ou `in-review`
3. La copie de travail revient sur la branche de base du projet

Si la copie de travail est sur une autre branche, aucune action n'est prise. Les erreurs git durant cette reprise sont loggées sans exception : un problème au redémarrage ne doit jamais bloquer le backend.

### Intégrité de la fiche lors de la reprise (ticket-377)

Quand une branche de ticket est reprise au démarrage, sa fiche est validée. Si le ticket a été déplacé de `tickets/todo/` vers `tickets/in-progress/` ou `tickets/in-review/` mais que ce déplacement n'a pas été committé (fichier non suivi), la reprise ajoute explicitement le fichier au commit « unapproved work ». Seule la fiche du ticket est ajoutée ; aucun autre fichier non suivi ne peut y entrer.

### Récupération des fichiers neufs et gestion des tickets approuvés (ticket-389)

Lors d'une reprise au démarrage, deux garanties préviennent la perte de travail :

**Fichiers non suivis créés pendant le run**

Les fichiers créés par le codeur après le `started_at` du run, mais non encore suivis par git, sont intégrés au commit de reprise — pourvu qu'ils ne soient pas ignorés (`.gitignore`) et qu'ils ne vivent pas dans un dépôt imbriqué (un dossier contenant un `.git` propre). Un fichier antérieur au `started_at` reste sur la branche de travail sans être commité : l'utilisateur peut y laisser des brouillons sans les perdre.

**Tickets approuvés mais non livrés**

Si un run avait atteint l'état `APPROVED` (fiche marquée `done` sur sa branche) avant d'être interrompu, la reprise ne le remet pas en `todo`. Il reste `done` et un événement est enregistré dans `memory/pipeline-log.md` : `[<ticket>] approuvé mais non livré : livraison à reprendre`. La livraison n'est pas relancée automatiquement ; elle demande une action manuelle.

### Dialogue pendant un run (ADR-025)

`DialogueChannel` porte les deux sens du dialogue sans rien savoir du
transport — ni WebSocket, ni SDK, ni LLM — ce qui rend la suspension, la reprise
et le mode autonome testables sans lancer un run.

- **L'agent demande** : l'outil `ask_user`, servi par un serveur MCP in-process,
  suspend le tour et attend. Une question est un appel d'outil structuré, pas un
  mot-clé cherché dans la prose (contrairement au verdict du reviewer, ADR-009,
  où rien de mieux n'existait).
- **L'utilisateur intervient** : les messages spontanés attendent dans une file
  distincte, vidée entre deux tours dans `build_context`. Les deux canaux ne se
  confondent jamais : un « pense aux tests » ne doit pas valoir réponse à « on
  casse l'API ? ».

Passé `dialogue_timeout_s`, l'agent reprend seul en **énonçant son hypothèse** :
un run suspendu tient du travail non commité, et bloquerait la file des tickets.
Une réponse qui arrive après l'expiration n'est pas perdue : elle est déposée dans
la boîte aux lettres comme message spontané, que l'agent lira au tour suivant.

L'interface affiche l'état de chaque réponse :

- **Transmise** (`answer_ack` avec `outcome: "transmitted"`) : la question et le
  champ disparaissent, remplacés par un accusé « Réponse transmise à l'agent. »
  (style `zinc`). Cet accusé est émis à tous les observateurs du run.
- **Déposée** (`outcome: "deposited"`) : la réponse attend le tour suivant, la
  question reste affichée.
- **Expirée** : sans réponse jusqu'au `agent_done`, elle s'affiche comme « Question
  expirée… » avec l'hypothèse de l'agent.

Lors du rejeu du journal du texte (quand l'utilisateur change de sélection ou
recharge la page), les événements texte (`agent_token`, `agent_tool_use`) ne
modifient pas l'état d'une question en attente. Seul un événement de réponse
(`answer_ack`) ou de fin d'agent (`agent_done`) nettoie cet état.

### Filtrage du contexte par rôle (ticket-379)

Chaque agent reçoit un contexte filtré selon sa portée définie dans les ADR du projet. Pour éviter que ce filtrage ne supprime le diff à relire, les résultats du testeur ou l'audit sécurité qui suivent les décisions, le contexte borde la section `Décisions récentes` à son premier titre de niveau 2 qui n'est pas un titre d'ADR (`## ADR-NNN`).

**Invariant** : le contexte d'un agent inclut toujours le diff git, les résultats des étapes précédentes et l'audit, indépendamment de la portée des ADR du projet. Seule la section des décisions elle-même est filtrée par rôle.

`adr_pertinents` (`backend/src/tessera/services/adr.py`) découpe à cette limite. Les ADRs au format `contraintes.md` (`contraintes_pour`) n'en ont pas besoin : leurs blocs s'arrêtent déjà au titre de niveau 2 suivant.

### Système visuel du frontend (ADR-026)

`frontend/src/design/` porte ce qui doit rester cohérent d'un panneau à l'autre :
`icons.tsx` (un seul jeu, grille de 24, trait 1.5), `layout.ts` (la hauteur unique des
bandes d'en-tête), `RegionTitle.tsx`, `InfoTip.tsx`, `StageStrip.tsx`. Cinq familles de couleurs ont chacune un
rôle d'état — neutre, échec, attente, succès, activité — et `violet` sert
uniquement au repérage.

`InfoTip` sépare les **explications** — affichées au survol et au focus d'une icône
button, `role="tooltip"` — des **états** et **appels à l'action** qui restent toujours visibles.
L'icône est liée au texte par `aria-describedby`. Ses couleurs sont zinc, pas de violet
en texte.

`StageStrip` (depuis ticket-256) affiche l'état de chaque étape du pipeline du run — 
production, tests, sécurité, revue, validation, documentation, livraison — en tête du panneau 
Agents. Chaque pastille représente une étape, avec trois états : faite (`green`), en cours 
(`blue`), à venir (`zinc`). Une étape désactivée pour le projet n'a pas de pastille. 
L'étape Tests n'apparaît que si le projet a un testeur. Un refus de l'audit sécurité, 
une validation rejetée, ou un échec des tests rendent leur pastille respective `red`. 

Après l'audit sécurité, reviewer et validateur peuvent tourner en parallèle (ticket-289) :
`StageStrip` marque `active` toute étape présente dans `etapesEnCours`, permettant 
d'afficher deux pastilles `blue` au même moment. Une étape n'est `done` que si son 
événement de fin a été reçu, ou si une étape qui la suit (et ne tourne pas en parallèle) 
a démarré.

`coherence.test.ts` verrouille les trois règles : il lit les sources et échoue
à la première réintroduction d'une couleur bannie, d'une taille de texte
arbitraire ou d'un glyphe utilisé comme affordance.

Ce système est imposé aux agents créant une interface via le skill `tessera:design-ui`, chargé par défaut par le codeur et l'architect : toute UI doit partir d'une charte déclarée (couleurs, typographie, espacement), et n'en sortir sur aucune valeur.

#### Composants UI partagés

Le frontend centralise les composants visuels dans `frontend/src/design/ui/`, pour respecter la charte et les familles de couleurs d'ADR-026 :
- `StatusPill.tsx` : pastilles d'état (en-cours, reussi, attention, echec, neutre)
- `Button.tsx` : boutons avec variantes plein/borde/discret/arret, tailles normal/compact
- `ViewSwitcher.tsx` : sélecteur horizontal de vue
- `ViewState.tsx` : états composites (vide, chargement, erreur)

Les trois sélecteurs de vue du frontend (Historique, Fichiers, Agents) utilisent `ViewSwitcher`, éliminant les copies locales et garantissant la cohérence visuelle.

### Limite de silence des agents (ticket-381)

Un processus d'agent qui n'émet aucun message pendant plus de `AGENT_SILENCE_MAX_S` secondes (défaut : 1200 s, soit 20 min) est interrompu.

L'attente se mesure **entre deux messages** du flux, pas la durée totale de l'appel. Un agent qui lance une commande longue (suite de tests : ~6 min) mais émet régulièrement n'est jamais arrêté.

Quand le silence est détecté :
1. Le flux est fermé (`aclose` appelé)
2. Le processus `claude.exe` est terminé
3. Une `ProviderIndisponible("agent silencieux depuis … s")` est levée
4. L'événement `agent_silencieux_arrete` est journalisé

Le repli ou l'échec fermé existant (ADR-037, ADR-039) reprend aussitôt le run ou en demande l'approbation.

Ce mécanisme ne détecte pas la veille du PC en tant que telle : il mesure le silence du flux. Deux cas réels qui l'ont motivé (octobre 2026) ont impliqué une veille du PC et un CLI bloqué.

## Endpoints implémentés

### Projets
| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/v1/projects` | Liste tous les projets (dossiers avec CLAUDE.md) |
| `POST` | `/api/v1/projects` | Crée la structure filesystem d'un projet |
| `GET` | `/api/v1/projects/{id}` | Charge le projet et son CLAUDE.md |
| `GET` | `/api/v1/projects/{id}/context` | Contexte complet (tickets ouverts + décisions) |
| `GET` | `/api/v1/projects/{id}/runs` | Historique des pipelines (SQLite, limite configurable) |

### Tickets
| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/v1/projects/{id}/tickets` | Liste les tickets (optionnel: `?status=todo`) |
| `POST` | `/api/v1/projects/{id}/tickets` | Crée un ticket (génère le fichier Markdown) |
| `GET` | `/api/v1/projects/{id}/tickets/{tid}` | Détail d'un ticket |
| `PATCH` | `/api/v1/projects/{id}/tickets/{tid}/status` | Déplace le ticket dans le bon dossier |

### Agents
| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/v1/agents/run` | Exécute un agent sur un ticket (sans streaming) |
| `WS` | `/api/v1/agents/stream` | Exécute un agent avec streaming de tokens |
| `POST` | `/api/v1/agents/create-project` | Crée un projet via conversation multi-tours |

### Orchestrateur
| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/v1/orchestrator/run` | Lance le pipeline codeur→reviewer (sauvegarde en DB) |
| `POST` | `/api/v1/orchestrator/run-autonomous` | Mode autonome (N tickets en séquence) |
| `WS` | `/api/v1/orchestrator/stream/{project_id}` | Stream des OrchestratorEvents + sauvegarde en DB |


#### Validation de configuration avant le run

Avant de lancer le pipeline sur un projet (`POST /orchestrator/run`), l'orchestrateur
vérifie que le projet est configurable pour sa stratégie de livraison :

- **Projet `autonomy: pr` ou `merge`** : exige à la fois `github_remote` (déclaré dans
  `agents.json` du projet) et `GITHUB_TOKEN` (variable d'environnement du backend).
- **Projet `autonomy: commit`** : aucune exigence GitHub — les changements restent locaux.

Si la vérification échoue — `github_remote` manquant, ou `GITHUB_TOKEN` absent — le serveur
rejette la requête avec un code **422**. Le message indique ce qui manque et comment
corriger (« ajoute `github_remote` dans agents.json » / « renseigne GITHUB_TOKEN »).

Le projet **n'est pas réservé** après ce refus : une tentative suivante, après correction,
s'exécutera normalement.

Cette vérification est une optimisation (ticket-413) : elle évite de dépenser un run complet
à découvrir à la livraison qu'on ne peut rien pousser.

## Flux d'un ticket

```
 1. Ticket en todo/ → POST /orchestrator/run { project_id, ticket_id }
 2. DB : create_run(project_id, ticket_id) → run_id
 3. Garde-fou : arbre de travail sale ? → ticket → blocked/, run terminé
 4. Orchestrateur: ticket → in-progress/
 5. git checkout -b ticket-XXX-slug  (forkée de la base synchronisée sur le 
    distant, pas du ticket précédent) → OrchestratorEvent.BRANCH_CREATED
    Avant le checkout, le pipeline commite les artefacts de tenue de livres
    (`memory/pipeline-log.md`, fichiers de `tickets/`) pour éviter qu'ils ne
    bloquent ce checkout. Toute GitWorkspaceError autre que NotAGitRepository
    arrête le run en `blocked`, sans appeler aucun agent.
 6. Codeur (Claude) → ÉCRIT RÉELLEMENT les fichiers (outils fichier du SDK)
    └─ tokens streamés via WS → UI en temps réel
    └─ chaque event → save_event(run_id, ...)
 7. git diff → c'est CE diff qui alimente toutes les étapes suivantes
    (repli sur la prose du codeur si le diff est vide)
 8. Testeur → exécute la suite complète de vérification (pytest, mypy, tsc, eslint) → TEST_RESULT
 9. Auditeur sécurité (OWASP) → BLOCK si CRITICAL/HIGH → ticket → blocked/
10. Ticket → in-review/
11. Reviewer (Claude) et Validateur tournent en parallèle
    ├─ Reviewer relit le diff
    ├─ Validateur vérifie les critères d'acceptation un par un
    ├─ Validateur reçoit aussi le contenu des fichiers cités dans les critères
    │  (pour juger un critère rempli par du code préexistant — ticket-316)
    ├─ Approuvé seulement si le reviewer approuve ET le validateur ne refuse pas
    ├─ Sur un refus, le codeur reçoit les motifs de tous les agents qui ont refusé
    └─ Retour au Codeur si refusé (max 3 tours ; sinon ticket → blocked/)
12. Doc-updater → met à jour README / docs / CLAUDE.md du projet (sauté si `light: true`)
13. Livraison Phase 1 (si approuvé) :
    ├─ Rebase de la branche du ticket sur la branche de base (sync du distant)
    ├─ Gestion des conflits : si conflit hors fichier ticket, rebase aborté et conflit tenté par resolveur-conflit (ADR-033)
    ├─ Push de la branche du ticket vers le distant
    ├─ Ouverture de la PR vers la branche de base → rend pr_number
    └─ Émission de `run_closed` — le run n'est plus vivant
    La phase 2 (attente CI + merge) se poursuivra asynchrone après le run via CIWatcher.
14. git commit — sur TOUS les chemins de sortie :
    ├─ approuvé      → "<type>: ticket-XXX — <titre>" puis advance_base_ref()
    └─ non approuvé  → "chore: ticket-XXX — unapproved work (<raison>)"
    (+ un second commit séparé pour la comptabilité Tessera :
     statuts de tickets et pipeline-log, jamais sous le message du ticket)
15. DB : finish_run(run_id, rounds, approved, final_status)
16. PipelineResult { ticket_id, final_status, rounds, approved, branch, commit_sha }
17. OrchestratorEvent.PIPELINE_DONE envoyé via WebSocket
```

**Invariants** (voir ADR-018) :

- Le commit est conditionné à la **réussite** de la création de branche : si le
  projet n'est pas un dépôt git, le pipeline continue sans committer plutôt que de
  committer sur une branche arbitraire. Toute autre erreur lors de la création de
  branche (GitWorkspaceError autre que NotAGitRepository) arrête le run en
  `blocked`, avec un `arret` qui cite l'erreur git, et aucun agent ne tourne.
- Seul un ticket **approuvé** fait avancer la ref de base. Le travail rejeté reste
  sur sa branche et ne contamine jamais le ticket suivant.
- Un fichier non suivi déjà présent au démarrage du run n'est jamais balayé dans le
  commit du ticket : il ne vient pas du codeur.
- Le verdict du reviewer est la première ligne qui commence par APPROVED ou CHANGES_REQUESTED. Une approbation qui nomme CHANGES_REQUESTED sur la même ligne est un refus ; sur les lignes suivantes, elle approuve (ticket-298, ADR-009).

### Testeur et timeouts (ticket-349)

`TestResult` porte un champ `expiree: bool = False` pour distinguer un timeout d'un vrai test échoué.

**Cas 1 : Test échoué ordinaire** (`expiree=False`, `passed=False`)
- Le codeur a écrit du code qui ne marche pas
- Le pipeline renvoie le ticket au codeur pour correction
- Comportement existant, inchangé

**Cas 2 : Premier timeout** (`expiree=True`)
- La suite de tests n'a pas terminé dans le délai autorisé
- Elle n'a rien prouvé sur le code
- Le pipeline rejoue la suite **une fois**, sur la même branche, espérant que la machine soit moins chargée
- Si la relance passe, le run continue normalement vers la sécurité
- Si la relance expire aussi, passage au cas 3

**Cas 3 : Deux timeouts consécutifs** (`expiree=True` deux fois)
- La suite expire malgré une relance
- Le run se termine en `blocked` avec raison « testeur: délai dépassé deux fois »
- Le commit est fait (comme toute sortie terminale)
- Le ticket n'est pas renvoyé au codeur et aucun tour n'est consommé
- Cet état signale un problème système (machine surchargée, délai configuré trop court) plutôt qu'un défaut du code

L'enregistrement du pipeline écrit « testeur: délai dépassé, suite relancée » dans le `pipeline-log.md` à chaque relance.


### Audit de sécurité

L'agent sécurité audite le diff avant la revue. Selon ADR-039, une réponse JSON invalide bloque toujours le run — aucun repli n'est possible pour le jugement de sécurité.

**Robustesse en cas de réponse invalide** (ticket-436) :

Quand le modèle rend un JSON non-valide du premier coup, l'IDE lui redemande une seule fois avec une consigne explicite : « Ta réponse précédente n'était pas un JSON valide ; réponds uniquement par l'objet JSON demandé. »

- Si la deuxième réponse est valide → elle fait foi, l'audit rend son verdict (PASS ou BLOCK)
- Si les deux réponses sont invalides → audit BLOCK avec motif indiquant deux réponses illisibles
- Exception du provider (timeout, erreur réseau) → pas de seconde tentative ; ADR-046 gère le fallback

Journal : `security_auditor_invalid_json` enregistre le numéro de tentative (1 ou 2) pour chaque réponse invalide.

### Résultats des tests et extraction d'erreurs (ticket-393)

Quand les tests échouent, `test_runner.py` extrait :

- **Résumé** : la ligne officielle de pytest/vitest (ex : `1 failed, 455 passed in 12s`)
- **Détails** (`failure_details` dans `TestResult`) : synthèse courte et bloc de défaillances, tronqués à 8 000 caractères

Le prompt du codeur (tour suivant) reçoit `failure_details`, remplaçant une liste brute. Le journal n'affiche que le résumé. Cela concentre l'attention sur le test échoué même quand des centaines passent.

### Validation et fichiers cités (ticket-316)

Le validateur vérifie chaque critère d'acceptation du ticket. Un critère peut être 
satisfait par du code préexistant — par exemple, un test nommé dans le critère existe 
depuis un ticket précédent, et n'apparaît donc pas dans le diff du run en cours.

Pour éviter que le validateur ne refuse un critère simplement parce que le code n'est 
pas visible dans le diff, le pipeline extrait tous les chemins de fichiers cités dans 
les critères (chemins entre backticks, noms de fichiers de test) et joint leur contenu 
actuel au message du validateur, dans une section distincte du diff. Cette section :

- Borne la taille totale pour limiter le contexte ;
- Signale tout fichier cité mais absent du dépôt ;
- Permet au validateur de juger des critères sur code préexistant.

Le prompt du validateur (`agents/prompts/validateur.md`) l'instruit sur cette section 
et sur le fait qu'un critère satisfait par du code visible dedans ne doit pas être refusé.

Les fichiers cités dans les critères d'acceptation (entre backticks) sont trouvés et joints au validateur pour qu'il puisse vérifier le travail. Pour un projet déclaré `git_root: ancestor` (comme ide-core), la recherche s'étend au dépôt git qui contient le projet, pas seulement à son dossier (ticket-448). Les garde-fous restent en place : aucun chemin absolu, aucun fichier hors de la racine du dépôt. Les textes entre backticks qui contiennent une espace (p. ex. `git ls-files CLAUDE.md`) sont ignorés, ce qui évite de confondre des commandes avec des noms de fichiers.

### Feedback du reviewer au codeur (ticket-474, ADR-009)

Après chaque passe du reviewer, le retour au codeur comprend le verdict et une raison détaillée.

**Extraction de la raison** : Le reviewer énonce son verdict seul sur sa ligne (ADR-009 — APPROVED, CHANGES_REQUESTED, etc.). La raison est le texte qui suit cette ligne ; s'il n'y a rien, la raison reste vide.

**Limitation de longueur** : Le retour stocké en `run.review_feedback` est limité à 4 000 caractères (augmenté depuis 500 en ticket-474 pour capturer les objections complètes). Au-delà, le texte est suffixé par « [...] tronqué ».

**Affichage dans le journal** : La ligne du pipeline affiche la première ligne non vide de la raison, pas le verdict seul. Cela permet au codeur de voir d'un coup d'œil la substance de l'objection — « interface manque un bouton » plutôt que juste « CHANGES_REQUESTED ».

## Synchronisation de la base au démarrage

Au début de chaque run, avant la création de la branche, si un espace git et une branche de base sont connus et que l'arbre se trouve sur la base, l'orchestrateur appelle `sync_base_depuis_distant(base_branch)` (ticket-406). Cette fonction met les lignes de journal non commitées de côté, avance la base par `merge --ff-only` depuis le distant, puis réécrit les lignes à la suite.

Un réalignement refusé — base locale divergente, autre fichier modifié, fetch impossible — n'empêche pas le run de partir. Le refus est journalisé (« base non réalignée — <raison> »), identiquement au réalignement entre deux tickets d'une file.

Aucune tentative de synchronisation n'est faite si l'espace git ou la branche de base est inconnu.

## Gestion des limites de session

Quand l'abonnement Claude atteint sa limite horaire, le CLI répond : « You've hit your session limit · resets <heure> ». Avant, le pipeline traitait cette erreur comme toute exception : le ticket passait en `blocked`, bloquant le projet.

Depuis le ticket-388, une erreur de limite de session provoque :
1. Le ticket en cours repasse en `todo` (son travail reste commité comme non approuvé)
2. La file s'arrête **avant** le ticket suivant
3. Un événement est émis portant `session_limit` comme raison et l'heure de reprise
4. Un log dans `memory/pipeline-log.md` : `[<projet>] file interrompue : limite de session (reprise : <heure>)`

Contrairement à `blocked`, `todo` ne bloque pas le projet. La file peut reprendre après l'heure indiquée. Aucun ticket n'est abîmé.

## Réalignement automatique du workspace avant un run (ticket-457)

Avant le lancement du pipeline, l'orchestrateur prépare l'arbre de travail si l'une des conditions est remplie :
- L'arbre n'est pas sur la branche de base du projet, OU
- Seul `memory/pipeline-log.md` porte des modifications non commitees

**Procédure** :
1. Sauvegarder les lignes non commitees du journal de pipeline
2. Revenir à la branche de base (reset hard)
3. Réaligner la branche locale sur le distant (`git pull --ff-only`)
4. Réappliquer les lignes sauvegardées du journal (union, sans doublon)

**Garanties** :
- Toute ligne du journal écrite précédemment reste présente une seule fois
- Tout autre fichier modifié bloque le départ du run — pas de nettoyage auto

**Contexte** : Après un run approuvé, la livraison en phase 2 (confiée au CIWatcher) écrit des lignes dans le journal *après* le commit de tenue de livres. Sans ce mécanisme, l'arbre resterait modifié, et le prochain run ne pourrait ni revenir à la base (arbre non propre) ni se réaligner (modifications bloquent le pull). Les tickets 378 et 406 ne couvraient que le cas où l'arbre était resté sur la branche de ticket — pas celui-ci.

## Documentation par lot (ADR-035, ticket-292)

Après approbation, le pipeline met à jour la documentation technique et fonctionnelle 
du projet — pas d'office, mais par lot, pour économiser les appels LLM sur les petits 
changements.

Un ticket peut se déclarer `light: true` dans son frontmatter. Les conséquences :

- Le run approuvé **saute** les étapes de doc-technique et doc-fonctionnelle
- Le marqueur d'avancement n'est **pas** avancé — le prochain lot partira du même point
- Le ticket suivant, non-léger, documentera **tous** les tickets depuis ce marqueur, 
  tickets légers compris
- Sécurité et validateur **tournent normalement** — ce sont des portes qui échouent 
  fermées (ADR-039), jamais optimisées

Cas limite : une file qui se termine sur des tickets légers les laisse sans documentation 
jusqu'à l'appel suivant d'un agent de documentation (mode autonome, chat, nouveau run).

## Livraison (ADR-029, ADR-030, ADR-051)

Après approbation du pipeline, la livraison s'enchaîne automatiquement — rebase 
sur la branche de base, ouverture de la PR, attente de CI si exigée, merge — 
jusqu'où le projet l'autorise. Cette séquence se scinde en deux phases (ADR-051) 
pour libérer le verrou dès l'ouverture de la PR et permettre au ticket suivant 
de commencer pendant l'attente de CI.

### Scission en deux phases

- **Phase 1** (`livrer_phase_1`) — s'exécute **dans le run du pipeline** : 
  rebase de la branche du ticket sur la base, push, ouverture de la PR. Retourne 
  le `pr_number`. Après succès, le verrou est libéré et le run peut terminer.
- **Phase 2** (`livrer_phase_2`) — s'exécute **après le run**, asynchrone via 
  `CIWatcher` : attente de CI si le projet l'exige, merge de la PR selon la 
  méthode déclarée. N'interfère jamais avec le ticket suivant.

Hors pipeline (appels directs depuis le chat ou l'interface), la méthode 
`livrer()` enchaîne les deux phases pour livrer entièrement en synchrone.

### Garanties de la phase 2 (ticket-328)

La phase 2 opère en arrière-plan, sans intervention humaine jusqu'au verdict final.
Trois garanties assurent qu'elle rapporte toujours comment elle a terminé :

**Exception capturée, verdict émis** : si une erreur survient pendant la phase 2
(erreur réseau, GitHub API indisponible, permission insuffisante), l'exception
est capturée et un `ci_merge_done` est émis avec `merged: false`. L'`arret`
porte le message d'erreur, et le ticket passe en `blocked` (ADR-051 : sans relance).

**Timeout** : la phase 2 entière est bornée dans le temps (merge et attente CI
comprises) — pas d'espoir de catch-all. Si elle ne rend pas la main avant ce
délai, un `ci_merge_done` est émis avec un `arret` qui dit que le délai est dépassé.

**Arrêt du backend** : une tâche de phase 2 en cours au moment du shutdown ne
génère pas de faux `ci_merge_done` d'échec. Seules les tâches complètement
terminées émettent leur verdict. Une tâche annulée reste non rapportée jusqu'au
redémarrage.

### Branche de base configurable

Un projet peut déclarer sa propre branche de base dans `agents.json`, champ 
`"base_branch"`. Par défaut (champ absent), on utilise `settings.github_base_branch` 
défini par la variable d'environnement `GITHUB_BASE_BRANCH` (défaut : `develop`).

Cette branche de base affecte :
- Le **rebase** de la branche du ticket avant l'ouverture de la PR
- La **cible** de la PR ouverte (elle vise cette branche)
- L'**avancement de la ref de base** après merge — seul un ticket approuvé en fait 
  avancer la ref, que le ticket suivant forkera

### Synchronisation de la base avant livraison

Au moment du rebase, la branche de base est alignée sur le distant pour 
assurer que le rebase se fait sur l'état réel. Un `fetch` met à jour les 
références locales ; la branche locale de base avance jusqu'au commit distant 
(avance rapide seulement). 

Sans distant joignable, le rebase utilise la base locale. Si elle a divergé 
du distant hors d'une avance rapide, la livraison s'arrête avec cette raison 
et ne procède pas au rebase.

### Commit des artefacts de tenue de livres avant rebase

Avant de rebaser la branche du ticket, la livraison commite tous les artefacts 
restants (`memory/pipeline-log.md` et fichiers de tickets) via `commit_bookkeeping`. 
Le pipeline enregistre des durées et des étapes dans le journal après la 
documentation, et ces lignes doivent être commitées avant le rebase — sinon 
l'arbre reste sale et `git rebase` échoue avec « You have unstaged changes » 
(ticket-303).

Seul un fichier de code modifié — celui qu'un agent aurait omis de committer — 
fait échouer la livraison, avec un message d'erreur explicite.

### Gestion des conflits de rebase

Pendant le rebase du ticket sur la branche de base, les conflits sont traités selon
leur nature :

**Fichier ticket** (le statut du ticket dans `tickets/todo/`, `in-progress/`, etc.) :
En cas de conflit sur ce fichier — modifié/supprimé ou modifié/modifié — l'IDE le
résout automatiquement en faveur de la branche du ticket. Le fichier porte le bon
statut pour son propre run et ne doit pas être jugé par un agent. Cette résolution
n'est jamais relue.

**Autres fichiers** : tout conflit est annulé (`rebase --abort`) et remonté à
un agent (resolveur-conflit, ticket-282), qui le tente sous relecture (ADR-033).
Aucune résolution automatique en dehors du fichier ticket.

**Annulation robuste** : si `rebase --abort` gêne des **fichiers non suivis**
portant les noms d'artefacts Tessera (`memory/`, `tickets/`, etc.),
l'IDE les met de côté et réessaie. En dernier recours, l'arbre revient à la
pointe d'origine de la branche du ticket, **sans perdre ce qui était commité**.
Après l'échec, `.git/rebase-merge` n'existe plus : l'arbre est propre pour le
ticket suivant, même en mode file.

#### Résolution automatique pour fichiers d'ajout seul (ticket-418)

Deux fichiers où chaque run ne fait que ajouter des entrées ne bloquent plus une livraison sur conflit de rebase :

- **`memory/pipeline-log.md`** : le service de préparation de l'espace git (avant chaque run) configure `merge=union` pour ce fichier dans `.git/info/attributes` du dépôt du projet. Ce paramètre reste en `.git/`, jamais versionné (configuration locale propre à chaque clone, voir ADR-021). Le pilote d'union natif à git résout automatiquement les conflits par concaténation ligne à ligne.

- **`memory/documentation.json`** : si c'est le seul fichier en conflit lors du rebase, il est résolu mécaniquement en prenant l'union des listes d'identifiants de run (JSON parcouru et réécrit en mémoire), puis le rebase continue.

Si d'autres fichiers sont en conflit, c'est un scénario complexe : le rebase s'arrête, la branche reste intacte, et un agent tente la résolution de ces ambiguïtés intrinsèques, toujours relue avant approbation (voir ADR-033). Cette automatisation élimine les blocages sur des fichiers où l'ajout séquentiel de deux branches ne crée aucune ambiguïté.

#### Appel du résolveur-conflit pour les conflits complexes

Quand l'auto-résolution échoue (fichiers modifiés des deux côtés, structures complexes), l'orchestrateur appelle le `resolveur-conflit` — un agent spécialisé en résolution de conflits (ADR-033) — **s'il est déclaré dans `agents.json` du projet**.

Si le résolveur n'est pas déclaré ou ne peut pas tenter, la ligne d'arrêt affiche : « résolveur non tenté : [raison] ». L'utilisateur peut alors ajouter le rôle dans `agents.json` et relancer le run.

### Délai de grâce pour l'enregistrement des checks

GitHub n'enregistre pas les checks de CI instantanément après l'ouverture 
d'une PR. Une interrogation immédiate retournerait `none` (aucun check enregistré), 
qu'ADR-029 traite comme l'absence de CI — un verdict qui arrêterait la livraison.

Pour éviter cette fausse absence, `LivraisonService._attendre_la_ci` applique 
un **délai de grâce** de 120 secondes (`grace_ci_s`, injectable au constructeur) :

- **Pendant le délai** : `none` se traite comme `pending` → continue d'attendre
- **Après le délai** : `none` devient un verdict final → livraison s'arrête
- **État `failing`** : arrête immédiatement, même pendant le délai

Un projet sans CI configurée attend donc ces 120 secondes supplémentaires avant 
abandon. Une configuration permet de contourner cette vérification pour les 
projets qui souhaitent merger malgré l'absence de CI.


Avant de conclure `none` (aucun check enregistré), la livraison vérifie que le dépôt a effectivement des workflows déclarés (`GET /repos/{repo}/actions/workflows`).

- **Dépôt sans workflows** : après le délai de grâce `CI_GRACE_S` (défaut 300 s), le statut passe à achèvement (`none` = pas de CI à attendre).
- **Dépôt avec workflows** : même après le délai de grâce, le statut reste `pending` jusqu'à `attente_ci_max_s`. C'est le cas où GitHub est lent à enregistrer les checks.

Sur une erreur réseau pendant la phase 2 (`httpx.TransportError`, dont `ReadTimeout`), le CIWatcher relit l'état de la PR avant d'abandonner. Si la PR est déjà mergée (`merged=True`), le run est marqué réussi avec un journal « mergée malgré une erreur réseau ». Tout message d'erreur inclut le type de l'exception, même si son contenu est vide (ticket-405).

### Arrêt sur permissions insuffisantes pour la CI

Quand le jeton GitHub ne peut pas accéder aux check-runs du dépôt (réponse HTTP 403 ou 404 sur l'endpoint `check-runs`), la livraison s'arrête immédiatement avec un message qui nomme les permissions manquantes, au lieu d'attendre le délai complet de CI.

`_get_ci_status` (github_service.py) rend l'état `"unreadable"` dans ce cas. `_attendre_la_ci` le reconnaît et l'arrête aussitôt, sans délai. La PR reste ouverte (ADR-030 : aucun merge sans CI lue). Une fois les permissions ajoutées au jeton, l'agent peut relancer le run.

`CIWatcher` applique la même logique quand il surveille le statut après l'ouverture de la PR.

### Méthode de merge configurable

Une PR de ticket est mergée selon la méthode déclarée dans `agents.json` du 
projet, champ `merge_method` (`squash`, `merge`, `rebase`). **Absent ou inconnu :
`squash`** — une PR est condensée en un seul commit.

En squash, le titre du commit reprend celui de la PR (conforme au format
Conventional Commits depuis le ticket-259) suivi du numéro `(#N)` — par exemple,
`feat: ticket-007 — Ajouter un endpoint (#42)`.

### Suivi après l'ouverture de la PR

Dès qu'une PR est ouverte, elle se voit assigner un `pr_number`. Celui-ci est écrit
dans le fichier du ticket et commité **avant** le merge de la PR, garantissant que
le `pr_number` remonte à la branche de base lors du merge. Aucun suivi n'est écrit
après le merge : la branche du ticket ne reçoit pas de commit une fois fusionnée.

#### Détection des PR non fusionables

Le CIWatcher lit le statut `mergeable_state` de la PR pendant l'attente de CI. Si ce statut devient `dirty` (la PR a un conflit avec la base), la surveillance s'arrête immédiatement avec une ligne d'arrêt dans `memory/pipeline-log.md`. Le ticket passe en échec, et les dépendants qui l'attendent le reçoivent aussi en échec (ticket-452).

#### Récupération d'une PR créée malgré une erreur réseau (ticket-455)

Quand l'appel d'ouverture de la PR échoue avec une erreur de transport (`httpx.TransportError`, notamment `ReadTimeout`), Tessera ne connaît pas le numéro de la PR créée — la livraison s'arrête sans pouvoir la confier au CIWatcher.

Pour récupérer cette PR orpheline, la phase 1 cherche une PR ouverte dont la branche de tête est celle du run courant (`GET /pulls?head=<owner>:<branche>&state=open`). Si elle existe, elle est traitée comme une `LivraisonInterrompue` avec `pr_orpheline=True` : elle passe au CIWatcher pour le suivi du statut CI. Si la recherche elle-même échoue ou qu'aucune PR n'est trouvée, l'arrêt d'origine est conservé sans nouvelle erreur.

#### Retry automatique pour les indisponibilités GitHub

Lors de la lecture du statut CI ou du merge d'une PR, une indisponibilité passagère de GitHub (502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout) n'arrête plus le run. Le CIWatcher réessaye jusqu'à trois fois avec une attente croissante (1 s, 2 s, 4 s) avant abandon définitif. Les erreurs 4xx (403 Forbidden, 404 Not Found…) ne déclenchent pas de retry — elles reflètent une vraie permission manquante ou une ressource disparue (ticket-461).

### Attente du statut mergeable avant le merge

Avant d'appeler l'endpoint de merge, `GitHubService` vérifie que la PR est 
fusionnable. GitHub calcule le statut `mergeable` de manière asynchrone peu après 
l'ouverture d'une PR — ce champ peut valoir `null` pendant quelques secondes.

Le processus :

- `GitHubService` lit la PR. Tant que `mergeable` vaut `null`, il attend et 
  relit, avec un délai maximum (60 secondes par défaut) pour éviter une 
  boucle infinie
- Si `mergeable` passe à `true`, le merge procède normalement
- Si `mergeable` devient `false`, la livraison s'arrête avec un `arret` explicite,
  sans appeler l'endpoint de merge
- Un statut HTTP 405 (`Method Not Allowed`) au merge — cas résiduel après l'attente 
  — est retenté une fois, puis remonté en `arret` si l'erreur persiste

Cette attente élimine les fausses erreurs 405 quand une PR est ouverte sur un 
projet avec `merge_without_ci: true`, qui merge immédiatement après approbation 
du pipeline, avant que GitHub n'ait eu le temps de calculer la fusibilité.


### Mise à jour de la base distante après merge en file

Quand la livraison opère en **mode file** (`queue`) sur un projet avec
`autonomy: merge`, le ticket suivant doit partir d'une base à jour. Après qu'une
livraison a mergé sa PR :

- Un `fetch` met à jour les références locales depuis le serveur
- La branche locale de base avance jusqu'au commit distant (avance rapide seulement)
- `_base_ref` est repositionné sur ce nouveau commit

Le ticket suivant forkera depuis ce commit, non depuis la branche du ticket
précédent. Un rebase n'aura donc pas de conflit factice avec le squash du ticket
précédent, déjà fusionné sur la branche de base distante.

**Cas non mergés** (ticket-302) : Si la PR du ticket n'a pas mergé — erreur CI,
conflits, ou autre raison — le ticket suivant part de la base distante, pas du
ticket précédent. Cela prévient qu'un ticket approuvé mais non mergé n'empoisonne
le ticket suivant.

Un ticket suivant qui déclare son prédécesseur dans `depends_on` arrête la
file. Le `arret` nomme la PR restée ouverte ; le ticket refusera d'avancer
tant qu'elle n'aura pas mergé.

**Divergence** : Si la branche locale et distante divergent hors d'une avance
rapide, la branche n'est pas réécrite ; la raison s'ajoute à `Livraison.arret`.

### Réalignement de la base locale après merge du CIWatcher (ticket-420)

Après qu'un run autonome soit mergé par le `CIWatcher` (`services/ci_watcher.py`), la base locale doit être réalignée sur la base distante pour que les services du projet servent le code à jour.

**Condition** : le réalignement ne s'effectue que si :
- Aucun run n'occupe actuellement le projet (`RUN_REGISTRY.projet_occupe()` retourne faux)
- L'arbre local est sur la branche de base configurée
- Les seules modifications locales portent sur `memory/pipeline-log.md`

**Procédure** :
1. Extraire les lignes du journal non encore commitées
2. `git checkout -- memory/pipeline-log.md` pour nettoyer le journal
3. `git pull --ff-only` pour aligner l'arbre sur le distant
4. Réécrire les lignes du journal qui n'y sont pas déjà présentes

**Cas d'erreur** : tout échec du réalignement (autre branche, autre fichier modifié, pull impossible, dépôt sur une autre branche) est journalisé avec raison (`realignement_ignore`) mais n'affecte pas l'état du run — `merged` reste vrai. Aucun fichier n'est modifié en cas d'erreur.

### État du dépôt après livraison (ticket-378)

Après la livraison d'un run, le dépôt local finit dans un état garanti :

- **Arbre propre** : aucune modification et aucun fichier non-tracké ; `git status --porcelain --untracked-files=no` est vide.
- **Retour à la branche de base** : la copie de travail est revenue sur la branche de base du projet (défaut : `develop`) ; aucun commit n'a été ajouté à cette branche pendant la livraison.
- **Logs dans le commit** : les lignes de livraison figurent dans le dernier commit de la branche du ticket (celui utilisé pour la PR), pas dans des commits orphelins de suivi.

Cela permet d'enchaîner plusieurs runs sans accumulation d'état en attente de nettoyage manuel.


### Finalisation de tous les runs et journalisation des défaillances (tickets-377, 390)

Après ticket-378, les tickets-377 et 390 étendent le nettoyage et la journalisation à tous les runs.

Quand une file ou un run s'arrête sur une exception, une ligne `[<projet>] file interrompue : <erreur>` est écrite dans `memory/pipeline-log.md` du projet pour le rendre visible dans l'IDE (ticket-377).

À la fin de tout run — qu'il aboutisse à une livraison, qu'il échoue en cours ou en fin de file — deux étapes finales sont franchies (ticket-390) :
1. `commit_bookkeeping()` — le journal du pipeline, les coûts et autres fichiers de suivi sont committés
2. `retourner_sur_base(base_branch)` — l'arbre revient sur sa branche de base

Les erreurs levées par ces étapes sont journalisées sans interrompre le run. Le retour ne touche pas à la branche du ticket : son commit reste où il est pour relecture future.

### Attente de fusionnabilité et gestion des dépendances (ticket-384)

Quand le statut `mergeable` d'une PR n'est pas encore calculé par GitHub (valeur `null`), l'IDE attend jusqu'à `ATTENTE_FUSIONNABILITE_MAX_S` (défaut 300 s) avant d'abandonner la tentative de merge. Le délai entre deux lectures augmente progressivement pour éviter de surcharger l'API.

**Échec d'une fusion** : Si une PR approuvée ne peut pas être mergée — conflit détecté par `mergeable: false`, ou dépassement du délai — le ticket passe en statut `blocked` (dossier *et* champ). Une ligne est écrite dans `memory/pipeline-log.md` : `[<ticket>] livraison: arrêt — PR #N non mergée : <raison>`. La file s'arrête.

**Dépendances interrompues** : Si un ticket A n'a pas été mergé, les tickets qui en dépendent ne sont pas lancés. La file s'arrête avec le message `[<projet>] file interrompue : <ticket> non mergé`. Résolvez A avant de relancer la file.

### Attente du merge pour les projets merge_without_ci (ticket-382)

Sur un projet déclarant `merge_without_ci: true` (merge sans attendre la CI), le pipeline évite les conflits de rebase en file.

Quand le projet est configuré pour fusionner sans CI, la file **attend le merge** du ticket courant avant de lancer le ticket suivant, indépendamment de ses dépendances déclarées. Un plafond `ATTENTE_MERGE_MAX_S` (600 secondes par défaut) prévient une attente infinie : au-delà de ce délai, le ticket suivant démarre et le fichier de log enregistre l'abandon.

Après le merge du ticket précédent (ou l'expiration du plafond), la base du ticket suivant est réalignée sur la base distante (`sync_base_depuis_distant`) avant la création de sa branche. Cette réalignement garantit que le nouveau ticket part du dernier état du dépôt distant.

Cette mécanique prévient les conflits causés par plusieurs tickets qui réécrivent les mêmes fichiers — en particulier `memory/architecture.md` et les guides de documentation — sans voir le changement du ticket précédent, qui a déjà fusionné.

Pour les projets avec une vraie CI, le comportement reste inchangé : le ticket suivant démarre sans attendre le merge (ADR-051) et n'attend que ses dépendances explicites (`depends_on`).

### Capture et dénomination des exceptions (ticket-415)

Quand une exception survient durant la phase 1 de livraison, elle doit être nommée lisiblement — y compris les exceptions sans message (`asyncio.TimeoutError`, `CancelledError` relayée, erreurs réseau). L'utilitaire `decrire_exception()` renvoie le message de l'exception s'il n'est pas vide, sinon son type (`TimeoutError`), toujours préfixé du type quand le message seul ne le contient pas.

La journalisation (`livraison_echouee`) inclut la pile complète (`exc_info=True`) pour aider au diagnostic.

**Cas critique** : une exception survient **après** l'ouverture de la PR. Le numéro de PR n'est jamais perdu — la `Livraison` le porte même en cas d'erreur, et la phase 2 (attente CI, merge) est confiée au `CIWatcher` comme pour une livraison réussie. Les PRs orphelines — ouvertes mais jamais relancées — ne peuvent donc plus se produire.

## Caching des statuts GitHub (ticket-364)

L'endpoint `/projects/{id}/tickets/{id}/pr-status` affichait le statut de chaque PR en interrogeant GitHub, sans cache. Chaque appel lancait deux requêtes GitHub (la PR, puis ses check-runs). Avec 139 tickets portant un `pr_number` dans ide-core, ouvrir le projet provoquait 139 appels à l'endpoint, soit ~280 requêtes GitHub — consommant 5,6 % du quota horaire (5 000 requêtes).

Le module `backend/src/tessera/services/pr_status_cache.py` implémente deux niveaux de cache :

- **Statuts définitifs** (`merged`, `closed`) : persistés dans une table SQLite `pr_status_cache`, relus sans appel GitHub — y compris après redémarrage.
- **Statuts ouverts** : gardés en mémoire 30 secondes, puis redemandés.
- **Erreurs** : jamais cachées.

`GitHubService.get_pull_request_status` et `github_workflow.py` restent inchangés : la livraison doit interroger GitHub en temps réel pour suivre la CI.

### Endpoint consolidé de statuts PR (ticket-366)

L'endpoint `GET /projects/{project_id}/pr-statuses` consolide l'état de toutes les PR d'un projet en une seule requête HTTP, éliminant le coût N du nombre de tickets. C'est le jour et la nuit sur un projet volumineux : 139 tickets sur ide-core le 2026-10-07.

**Optimisations appliquées** :

1. **PR réglées** (merged/closed) : rendues depuis la base sans appel GitHub
2. **PR absentes de la base** : listées une seule fois via `GET /repos/{repo}/pulls?state=all&per_page=100`, paginée jusqu'à épuisement ou trouvaille complète
3. **PR réglées retrouvées** : écrites en base pour les futurs appels
4. **PR ouvertes** : leur statut CI est vérifié avec le cache mémoire 30 s (ticket-364)
5. **PR orphelines** (`pr_number` hérité d'un autre dépôt, ticket-217) : omises sans erreur

L'endpoint par ticket reste en place : rien d'autre ne change.

### Cache et rafraîchissement intelligent du frontend (ticket-367)

L'endpoint `pr-statuses` retourne l'état de tous les PR d'un projet, mais c'est une seule fois au montage du composant qui affiche les cartes. Un hook `usePrStatuses` (`frontend/src/hooks/usePrStatuses.ts`) gère le cache côté frontend avec une stratégie de rafraîchissement intelligente :

- **Charge au montage** du composant contenant les cartes (Sidebar/TicketList.tsx, KanbanView)
- **Rafraîchit toutes les 30 s seulement** tant qu'au moins une PR est `open` ; arrêt complet dès que toutes sont réglées
- **Pause quand la fenêtre est cachée** — intégration `useFenetreVisible` (ticket-356) : aucun appel en arrière-plan
- **Rend une table** `ticket_id → PR status`, consommée en prop par chaque `TicketCard`

Chaque carte reçoit son statut en prop et n'émet aucun appel réseau — elle affiche ce qu'elle reçoit. Le rendu (badge « PR #N », info-bulle d'état, couleurs de CI) reste identique à l'utilisateur. L'économie est drastique : au lieu de N requêtes par ouverture (une par carte, souvent 50–150 sur les gros projets) plus un rafraîchissement N toutes les 30 s, c'est un appel unique par ouverture du projet, plus un toutes les 30 s si une PR est ouverte.

Cette consolidation suit le même principe que le ticket-365 (arrêt du polling pour une PR réglée), mais au niveau du projet entier : dès qu'aucune PR n'est ouverte, les appels s'arrêtent complètement.

## Vue d'ensemble et caching des projets (ticket-398)

L'endpoint `GET /api/v1/projects/overview` consolide en une seule requête tout ce qu'une fiche projet affiche : métadonnées, dates de création et activité, comptage des tickets par statut, état d'un run actif, présence d'une icône.

C'est l'application au catalogue des projets de la même optimisation qu'on a appliquée aux statuts GitHub (tickets 364–367) : plutôt que N requêtes, l'IDE n'en fait qu'une.

### Caching par projet

Les calculs git — dates de création et activité — et le comptage des tickets sont cachés par projet. Le cache s'invalide quand la date de modification change pour `.git/HEAD`, `.git/refs/heads/` ou le dossier `tickets/`. Deux appels de suite sans changement ne relancent aucune commande git.

C'est particulièrement important pour ide-core (`git_root: ancestor`) : les dates doivent porter sur le dossier du projet seul, pas sur tout l'ancêtre.

### Servage des icônes du projet

`GET /api/v1/projects/{project_id}/icon` sert la première icône trouvée dans une liste de chemins fixes — `frontend/public/favicon.svg`, `frontend/public/favicon.png`, `frontend/public/icon.svg`, etc. **Aucun chemin n'est reçu de la requête** : cela prévient tout accès à un fichier arbitraire du projet. Pas de fichier trouvé → `404`.

Chaque projet est associé à une icône, cherchée dans cet ordre :

1. `.tessera/icon.svg` — icône personnalisée, exclue de git par le projet (pour les cas où l'application n'a pas d'icône publique : scripts, bibliothèques, services)
2. Chemins web standards : `src/app/icon.svg`, `src/app/icon.png` (Next.js), `frontend/public/logo.svg` (React), `public/icon.svg`
3. `favicon.svg` ou `favicon.png` à la racine (pages statiques)

Pour un projet déclaré `git_root: ancestor` (qui habite un sous-dossier d'un dépôt), la recherche s'effectue aussi à la racine du dépôt qui le contient, dans le même ordre. Un projet frère sans `.tessera/icon.svg` ni chemin standard ne reçoit pas d'icône (ticket-404).

### Caching des services (ticket-410)

Chaque carte de projet dans la vue d'ensemble affiche deux états :
- `services_declares` : le projet a-t-il déclaré des services dans `agents.json` ?
- `services_en_cours` : au moins un de ces services est-il en cours d'exécution ?

Contrairement aux autres champs de `ProjectOverview`, ces deux états ne sont **jamais cachés** : ils sont calculés à chaque appel sur l'état réel :

- `services_declares` lit `load_services_config` à la racine du projet
- `services_en_cours` interroge `PROCESS_REGISTRY` pour y chercher un service vivant du projet

Cette absence de cache garantit qu'une nouvelle requête `GET /api/v1/projects/overview` reflète immédiatement les changements : un service démarré entre deux appels apparaît aussitôt, de même qu'un arrêt.

### Contrôle des services depuis les cartes (ticket-411)

Chaque carte de projet affiche un bouton de contrôle de service (« Lancer » ou « Arrêter ») si le projet déclare un service (`services_declares`). Le clic appelle `api.services.start` ou `api.services.stop` sans naviguer, puis relit la vue d'ensemble pour refléter le nouvel état.

**Invariants d'interaction** :
- Le clic sur le bouton **n'appelle pas** `onSelect` : `stopPropagation` bloque la sélection de la carte et la navigation
- Le bouton est désactivé pendant l'appel API
- Un échec affiche un message court sous le bouton en rouge (ADR-026) et laisse le bouton réactivé
- Pas de bouton si `services_declares` est faux

Le rechargement de la vue d'ensemble (`/api/v1/projects/overview`) après succès tient les états à jour en cas de lancements parallèles depuis plusieurs sessions.

### Détection des services locaux (ticket-416)

Tessera détecte et peut arrêter les apps de projet qui tournent localement, qu'elles soient lancées par l'IDE ou manuellement, pour libérer les ressources.

L'endpoint `GET /api/v1/services/running` énumère chaque app avec les champs :

- `project_id`, `project_name` : projet auquel elle appartient
- `nom`, `pid` : nom du service et identifiant de processus
- `origine: "tessera" | "externe"` : lancée par l'IDE ou détectée en dehors
- `ports: [int]` : ports écoutés
- `demarre_a` : timestamp de lancement
- `memoire_mo` : consommation mémoire RSS en Mo

**Services `tessera`** — enregistrés dans `PROCESS_REGISTRY` (lancés par l'IDE). Mémoire incluant les descendants du processus.

**Services `externe`** — processus écoutant un port déclaré par un projet (`--port N` dans une commande d'`agents.json`, ou `server.port` dans `vite.config.ts`) mais lancés en dehors de l'IDE. Détection cherche tous les ports du projet, exclut 8100 (backend Tessera) et 5173 (frontend Vite).

Mesure de mémoire : `psutil` si disponible (le backend le teste au startup) ; sinon repli sur `netstat -ano` + `tasklist` sous Windows, `ss` + `ps` ailleurs — interface unique derrière un mock testable (ADR-031).

L'endpoint `POST /api/v1/services/running/{pid}/stop` arrête l'arbre de processus, seulement si ce pid figure dans l'inventaire courant (404 sinon). Services `tessera` passent par `PROCESS_REGISTRY.arreter` ; services externes sont tués directement.

#### Attribution aux projets (ticket-435)

Une app externe n'est attribuée au projet que si son processus (ou parent direct) s'exécute sous le dossier du projet — chemins résolus, casse Windows ignorée.

Un port déclaré occupé par un processus étranger apparaît comme avertissement, sans pid arrêtable. L'endpoint `POST /services/running/{pid}/stop` refuse (404) pour ces avertissements.

Le projet qui fait tourner l'IDE n'a jamais d'app externe.

### Vue « En cours » (ticket-417)

La vue « En cours » supervise les services de projet actifs sur la machine, exposant
les endpoints d'arrêt implémentés par ticket-416 (`GET /api/v1/services/running` et
`POST /api/v1/services/running/{pid}/stop`).

**Polling autonome** : la liste se met à jour toutes les 10 secondes tant que la vue
est visible. Ce polling est suspendu quand l'utilisateur quitte la vue (gestion de
visibilité fenêtre, ticket-356), réduisant la charge en arrière-plan.

**Affichage et tri** : en tête, le total de mémoire consommée par tous les services.
La liste, groupée par projet et triée par mémoire décroissante, affiche par service :
le nom du projet et du service, son origine (Tessera ou externe), ses ports en liens,
sa durée et sa consommation mémoire, plus un bouton d'arrêt.

**Arrêt sélectif** : un service lancé par l'IDE (Tessera) s'arrête immédiatement.
Un service externe demande une confirmation avant d'être tué, afin d'éviter une
interruption accidentelle. Après l'arrêt, la liste est rechargée.

**États** : vide (aucune app active), chargement (récupération en cours), ou erreur.

## Contrôle des termes interdits dans la livraison (ADR-048, ADR-050)

Après approbation du pipeline, avant l'ouverture de la PR, `GitHubWorkflowService`
applique un contrôle : la `TermesInterditsService` rejette tout terme déclaré dans
`FORBIDDEN_TERMS` s'il apparaît dans le diff, les messages de commit, ou les
auteurs. L'exception : un projet marqué `"confidentiality": "professional"` en
`agents.json` contourne ce contrôle.

Deux étapes complètent la protection hors du pipeline :

1. **Hook pre-push** (`make install-hooks`) : rejette les commits manuels
   violant les termes.
2. **Job CI** (`.github/workflows/ci.yml`) : refuse la PR si `FORBIDDEN_TERMS`
   est absent (erreur de configuration) ou si une violation est détectée.

En local, une liste vide désactive le contrôle. En CI, son absence bloque le
merge — c'est intentionnel.


## Gestion des signalements en attente (ticket-421)

Quand un signalement (`POST /api/v1/signalements`, ticket-407) arrive pendant qu'un run ide-core est actif, il n'est pas écrit immédiatement dans l'arbre. Cela évite qu'il soit emporté dans le commit du run en cours — ce qui poluerait le diff réel avec une métadonnée Tessera.

**Flux** :

1. Requête `POST /api/v1/signalements` reçue
2. Vérification : `RUN_REGISTRY.projet_occupe("ide-core")` ?
   - **Oui** : le signalement est écrit dans `signalements_en_attente.json` (à côté de la base SQLite, sous `settings.ide_db_path`) ; réponse **202** avec `{ "en_attente": true, "position": n }`
   - **Non** : comportement standard, ticket créé dans `tickets/todo/` ; réponse **201**
3. À la fermeture du run ide-core (évènement de fin ou appel `RUN_REGISTRY.fermer`), les signalements en attente sont convertis en tickets et écrits, en ordre d'arrivée, chacun recevant un numéro distinct
4. Fichier `signalements_en_attente.json` vidé

L'ordre est garanti : deux signalements reçoivent des `position` croissantes et sont écrits dans cet ordre.

## Validation des identifiants de projet (ticket-370)

Toutes les routes contenant un paramètre `project_id` valident cet identifiant pour assurer que le chemin du projet reste conforme au dossier des projets configuré. Un `project_id` invalide — contenant `.`, `..`, `/`, `\` ou tout caractère ne correspondant pas au pattern `^[A-Za-z0-9][A-Za-z0-9._-]*$` — retourne une `404` sans jamais accéder au disque.

La validation est centralisée dans `backend/src/tessera/services/project_loader.py` :

1. **Paramètres de chemin** — FastAPI refuse un identifiant invalide avant l'appel du routeur (→ `404`)
2. **Corps de requête** — les objets `RunRequest` et `RunAutonomousRequest` rejettent un `project_id` invalide (→ `422`)

Cette approche centralise la prévention des path traversals pour l'ensemble des routes via une seule décision.

## Couche SQLite (ticket-015)

SQLite est une couche **cache/historique** — les fichiers Markdown restent la source de vérité (ADR-003).

```sql
-- Enregistre chaque exécution de pipeline
CREATE TABLE pipeline_runs (
    id           TEXT PRIMARY KEY,   -- UUID
    project_id   TEXT NOT NULL,
    ticket_id    TEXT NOT NULL,
    mode         TEXT NOT NULL DEFAULT 'single', -- 'single' | 'queue' | 'autonomous'
    started_at   TEXT NOT NULL,      -- ISO 8601
    finished_at  TEXT,
    rounds       INTEGER,
    approved     INTEGER,            -- 0 ou 1
    final_status TEXT                -- "done" | "blocked"
);

-- Chaque event WebSocket émis pendant le pipeline
CREATE TABLE agent_events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    TEXT NOT NULL REFERENCES pipeline_runs(id),
    type      TEXT NOT NULL,         -- "agent_started" | "agent_token" | ...
    agent     TEXT,                  -- "codeur" | "reviewer" | null
    data_json TEXT,
    ts        TEXT NOT NULL
);

-- Un appel LLM d'un run — tous les rôles (backend/src/tessera/services/database.py)
CREATE TABLE agent_calls (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            TEXT NOT NULL REFERENCES pipeline_runs(id),
    ticket_id         TEXT NOT NULL,
    role              TEXT NOT NULL,   -- "codeur" | "reviewer" | "securite" | "validateur" | ...
    model             TEXT NOT NULL,   -- modèle qui a répondu, repli compris
    input_tokens      INTEGER NOT NULL DEFAULT 0,
    output_tokens     INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd          REAL NOT NULL DEFAULT 0.0,  -- 0.0 pour ollama ; estimation sinon
    duration_ms       INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL,
    provider          TEXT NOT NULL DEFAULT ''    -- ajoutée par migration
);
```

**Mode et statistiques** : la colonne `mode` (ajoutée par migration depuis ticket-263) distingue les runs de tickets (`single`) des enveloppes de pipeline (`queue` pour une file, `autonomous` pour un run autonome). Les statistiques — nombre de runs, taux d'aboutissement, runs récents — n'incluent que les lignes `mode = 'single'` ; les enveloppes sont conservées pour tracer les événements WebSocket, mais ne comptent pas dans les totaux. Les coûts et tokens restent attachés aux appels d'agents enregistrés dans `agent_calls`, pas à la ligne d'enveloppe.

WAL mode activé pour éviter les locks en écriture concurrente.
`tessera.db` configurable via `IDE_DB_PATH` (default: `tessera.db` à la racine du projet).

### Isolation des tests de la base de production

Les tests du backend (`pytest`) redirectent `settings.ide_db_path` vers un fichier SQLite temporaire pour chacune de leurs exécutions (fixture `autouse` dans `backend/tests/conftest.py`, ticket-422). Aucun run de test n'écrit jamais dans `backend/tessera.db`, même quand les tests lancent le serveur complet via `TestClient(app)`.

## Récupération de l'historique d'un run (ticket-280, ticket-281, ticket-327)

Un run qui quitte la supervision — fermé ou au redémarrage du backend — disparaît 
de la WebSocket temps réel. Les événements persistent en SQLite et peuvent être 
rechargés lors d'une visite de l'historique, ou lors d'un rechargement de page 
si le run est encore en cours.

Deux entrées permettent de consulter un run terminé :

- **Panneau du ticket** : un bouton « Revoir le run » s'affiche si le ticket a un 
  run terminé, ouvrant la vue avec tous les événements enregistrés ;
- **Supervision** : une carte d'un run clos propose « Revoir le run » pour consulter 
  son déroulé complet.

Un endpoint léger, `GET /projects/{id}/tickets/{ticket_id}/runs`, rend la liste 
des runs du ticket, du plus récent au plus ancien, **sans calculer les statistiques** 
longues. C'est cet endpoint qui alimente le bouton « Revoir le run » depuis le 
panneau d'un ticket.

La vue rouverte affiche toujours le numéro du ticket et « Run terminé » quand le 
run est clos, même pour un ticket joué dans une file (où l'événement `run_closed` 
n'est pas émis lors du rejeu).

### Rechargement d'un run vivant

Lors d'un rechargement de page, l'écran découvre les runs en cours via 
l'instantané (`RunActif`). Si le run est vivant (en cours d'exécution), l'écran 
charge automatiquement ses événements historiques enregistrés :

1. Le frontend utilise le `db_run_id` de l'instantané pour appeler l'endpoint 
   du ticket-280
2. Les événements du début du run jusqu'à l'instant du rechargement sont retournés 
   en entier
3. Le frontend les rejoue dans `applyEvent`, la même fonction qui applique les 
   événements temps réel
4. Après le rejeu complet, le frontend se reconnecte à la WebSocket et reçoit 
   les événements en direct
5. Un mécanisme de déduplication écarte les événements reçus à la fois par 
   l'historique et par le flux en direct (ticket-313)

L'écran retrouve l'état du run tel qu'il était avant le rechargement. Un 
rechargement pendant le tour du codeur affiche le plan initial, tous les tours 
antérieurs, et reçoit ensuite les événements en direct du tour en cours.

### Visualisation des runs terminés

Un utilisateur peut aussi consulter l'historique en cliquant sur une ligne 
de `RecentRuns` :

1. **Récupération** : le clic appelle l'endpoint du ticket-280 avec l'identifiant 
   du run en base SQLite
2. **Rejeu** : le frontend applique chaque événement dans `applyEvent` — le même 
   code que pour la WebSocket temps réel. L'état visuel se reconstruit entièrement 
   en quelques millisecondes, cartes comprises.
3. **Lecture seule** : la vue rouverte n'affiche ni bouton d'arrêt, ni champ de 
   message, ni chrono qui tourne. C'est un instantané interactif du passé, pas 
   un run vivant.

### Invariants du rejeu

Cette capacité de rejeu repose sur le fait que chaque événement porte assez 
d'information pour reconstituer l'état. Les `OrchestratorEvent` — conçus 
initialement pour le temps réel — servent tout aussi bien au rejeu historique : 
c'est la même sérialisation JSON, les mêmes champs, aucune adaptation.


## Gestion des événements en file (ticket-313)

Un mode file traite plusieurs tickets en séquence. Le pipeline enregistre l'historique complet de tous les événements (Pipeline log, SQLite) pour l'audit et la traçabilité. Mais côté interface, **chaque ticket affiche son propre état d'étapes**, vierge au démarrage.

À chaque nouveau ticket (`queue_progress`), les événements du ticket courant repartent de zéro :

- Les pastilles de `StageStrip` reflètent l'état du ticket **en cours**
- Le ticket suivant démarre avec une bande d'étapes vierge (production à faire, sécurité à venir, etc.)
- Le Pipeline log accumule tous les événements de tous les tickets et reste complet

### Rejouer un run fermé sans dupliquer le texte

Quand un utilisateur revient à un run depuis la Supervision, le serveur rejoue le contenu textuel accumulé. Un aller-retour entre deux runs recevrait le même rejeu deux fois. Pour prévenir une duplication visible, le client traite les événements replayed de manière à garder une trace fidèle du texte — ni doublon, ni perte.

### Gestion du budget en file

En mode autonome (un seul ticket), le plafond d'un run est `RUN_MAX_BUDGET_USD` (5$ par défaut). En mode file (plusieurs tickets), le plafond s'étend : `RUN_MAX_BUDGET_USD` × nombre de tickets de la file. Cela évite qu'une file longue s'arrête prématurément sur un plafond pensé pour le mode autonome.

Une requête peut surcharger ce calcul en fixant `budget_usd` : ce montant devient le plafond pour ce run, en autonome comme en file.

Quand le plafond est atteint, le run s'arrête et émet un événement portant `budget` comme raison.

## Gestion de l'état du frontend — store des runs (ticket-354)

L'état de chaque run vit dans un store externe (`frontend/src/hooks/runStore.ts`) utilisant `useSyncExternalStore`, pas dans un objet `etats` remonté jusqu'à `App`. Un événement d'un run redessine uniquement les composants qui l'affichent, réduisant drastiquement les re-renders inutiles.

**Sélecteurs** — Les composants ne lisent jamais le store directement :
- `useEtatRun(runId)` — Ne redessine que si le run change.
- `useListeRuns()` — Ne redessine que si la liste ou un statut change (pas sur `agent_token`).

**Optimisations** — `Sidebar`, `TicketCard`, `KanbanView` en `React.memo` avec props stables, pour éviter les re-renders en cascade. ADR-013 : la solution reste en React pur, sans Zustand.

## Caching des ressources et gestion de la visibilité fenêtre (ticket-356)

Quand l'utilisateur revient sur un ticket ou un projet déjà ouvert, l'application doit afficher immédiatement la donnée précédemment vue (pas d'écran de chargement), puis rafraîchir en fond. Parallèlement, le polling (rechargement périodique) doit cesser quand la fenêtre est cachée, pour économiser quota et CPU.

### Caching au niveau du module

`useResource(fetcher, initial, cle?)` peut accepter une clé optionnelle (chaîne). Avec clé :
- La dernière donnée obtenue est gardée dans un cache de niveau module (LRU, 100 entrées max)
- Au changement de `fetcher`, la données en cache est rendue **aussitôt** au composant, avec `loading: true`
- Un rafraîchissement part en fond ; quand il arrive, l'état est mis à jour sans défilement intempestif
- La clé inclut toujours l'id du projet, pour qu'une donnée d'un autre projet ne s'affiche jamais

Sans clé, `useResource` a le comportement actuel : changement de `fetcher` → rendu de `initial` immédiat, puis fetch.

Cette décision répond à deux cas d'usage :
1. Ouvrir un ticket, fermer le panneau, rouvrir le ticket → voir immédiatement les données
2. Cliquer d'avant en arrière dans un historique → pas d'écrans blanc

### Suspension du polling hors vue

`useFenetreVisible()` lit `document.visibilityState` et expose un booléen qui se met à jour sur `visibilitychange`. Les trois points de polling (`useTickets`, `useServices`, et le polling de statut PR dans `TicketCard`) utilisent ce hook pour :
- Suspendre leur intervalle quand `visibilitystate === 'hidden'`
- Relancer une requête immédiate au retour en avant-plan

Cette optimisation diminue significativement le nombre d'appels API quand plusieurs onglets ou fenêtres sont ouverts mais non actifs.


### Arrêt du polling pour PR réglées (ticket-365)

Une optimisation de ticket-365 raffine le mécanisme précédent. Quand la PR passe à `merged` ou `closed`, le composant `TicketCard` arrête le polling **définitivement** : l'appel `getPrStatus` n'est plus relancé, même quand la fenêtre redevient visible. Seules les PR `open` gardent le cycle pause/reprise (suspension fenêtre cachée, reprise à la réapparition).

Cette optimisation élimine les appels redondants sur les cartes dont la PR est réglée depuis longtemps.

## Vue Historique (ticket-427)

Chaque onglet du cockpit affiche une vue différente au centre : Tickets, Agents, Usage, Chat, ou Historique.

`CenterView.tsx` route vers le composant approprié selon le panneau actif (`panel`). L'onglet **Historique** rend `HistoriqueView`, qui remplace la liste de tickets pour montrer l'historique des runs du projet.

### Structure de HistoriqueView

La vue Historique offre deux modes, sélectionnables via un en-tête avec deux boutons :

1. **Détail du run** (défaut) : affiche le détail du run sélectionné ou le plus récent. Affiche le ticket, son titre, le verdict du run, le nombre de tours, et le fil complet du run rendu par `RunHistorique` (ticket-281). Sans run sélectionné : le plus récent ; sans aucun run : l'état vide.

2. **Tous les runs** : tableau filtrable de tous les runs du projet. Colonnes : ticket, titre, verdict, nombre de tours, coût, date. Filtres : « Tous », « Approuvés », « Refusés ou bloqués ». Le filtre « Plusieurs tours » garde seulement les runs avec `rounds > 1`. Un clic sur une ligne ouvre le détail de ce run.

### Interaction avec la colonne de gauche

La colonne de gauche (`RunHistory.tsx`) liste les runs du projet. Un clic sur un run **sélectionne ce run** dans l'état du cockpit (à côté du ticket sélectionné), ce qui met à jour `HistoriqueView` pour afficher son détail. Le sélecteur de run est distinct du sélecteur de ticket.

### Couleurs et statuts

Les verdicts des runs sont colorés selon ADR-026 : vert approuvé, ambre plusieurs tours, rouge refusé ou bloqué.

## Structure des fichiers de tickets

```
projects/{project_id}/tickets/
  todo/         ← prêts à être pris en charge
  in-progress/  ← codeur en cours
  in-review/    ← reviewer en cours
  done/         ← approuvés
  blocked/      ← 3 tours sans approbation
  archive/      ← > 30 jours en done
```

Chaque ticket = fichier Markdown avec frontmatter YAML :
```yaml
---
id: ticket-007
title: Frontend scaffold — Vite + React + Tailwind
type: feat          # feat | fix | chore | design | docs
status: todo
priority: high      # critical | high | medium | low
agent: codeur
depends_on: []
created: 2026-06
github_issue_url: https://github.com/...  # optionnel
---
Corps du ticket en Markdown...
```

Les tickets créés par lot depuis un plan conservent leurs critères d'acceptation : le corps du ticket inclut une section `## Critères d'acceptation` avec une case à cocher par critère (`- [ ] …`). Ce format est directement lisible par `_extract_criteria` et permet au validateur de juger chaque critère indépendamment.


### Extraction des critères d'acceptation

Les critères d'acceptation d'un ticket sont extraits du corps Markdown par le service `pipeline_text`. La section de critères commence dès qu'une ligne **commence** par `## Critères d'acceptation` (insensible à la casse, ignorant l'indentation). Les références au titre dans la prose — même entre backticks, même sur la même ligne — ne sont jamais prises pour un en-tête réel.

Chaque ligne non vide de la liste de critères devient un critère distinct. Un critère dont le texte cite le titre (ex. « Vérifier `## Critères d'acceptation` en début de ligne ») reste lisible et est compté normalement. Cette règle évite les faux positifs où une citation du titre de section dans le contexte ou la prose aurait fermé prématurément la section avant les vrais critères.

### Validation des tickets avant commit (ticket-433)

La fonction `verifier_tickets(racine_projet)` exécute les mêmes validations que `TicketService` au chargement, et renvoie une liste de problèmes — ou une liste vide si tous les tickets sont valides.

Elle signale :
- Un champ hors enum (ex. `type: invalid`) avec le chemin du fichier et le nom du champ
- Un fichier rangé dans le dossier qui ne correspond pas à son `status` (ex. `status: done` dans `todo/`)
- Deux fichiers portant le même `id`

Un `created` lu par YAML comme une date (ex. `2026-10-14`) est accepté.

Trois interfaces la proposent :
- **Endpoint** : `GET /api/v1/projects/{id}/tickets/check` renvoie `{ "valides": true, "problemes": [] }`
- **Commande Make** : `make check-tickets PROJET=<id>`
- **Script PowerShell** : `.\scripts\tessera.ps1 check-tickets <id>`

Elle s'intègre dans le workflow de vérification avant commit : si elle signale un problème, la branche locale n'est pas committée.

## Chat conversationnel (ticket-048, 225)

Une conversation libre sur un projet, distincte du pipeline : l'agent a le
contexte projet, lit et écrit les fichiers, et streame sa réponse.

| Méthode | Route | Rôle |
|---------|-------|------|
| `GET` | `/api/v1/projects/{id}/chat` | Liste des conversations |
| `GET` | `/api/v1/projects/{id}/chat/{conversation_id}` | Historique + coût d'une conversation |
| `WS` | `/api/v1/projects/{id}/chat` | Un tour de conversation, streamé |

**Plusieurs conversations (ticket-225)** : un projet peut avoir plusieurs conversations, listées et gérées par l'UI. L'utilisateur peut en créer une nouvelle (nouvel identifiant) ou reprendre une ancienne. La conversation `"default"` persiste si elle existe. Le frontend passe le `conversation_id` au backend pour chaque tour.

Trames WebSocket : `start`, `token`, `tool_use`, `done`, `budget_exceeded`,
`error`.

**Outils** : `Read`, `Write`, `Edit`, `Glob`, `Grep`. **Aucun outil shell** —
un agent conversationnel exécutant des commandes arbitraires dans le dépôt de
l'utilisateur est une surface d'attaque refusée par le ticket.

**Cohabitation git (ADR-019)** : les écritures du chat sont commitées sur une
branche `chat-<horodatage>`, exactement comme un run de pipeline sur la branche
de son ticket. Sans ça, l'arbre resterait sale et le ticket suivant partirait
en `blocked` sans qu'aucun agent n'ait tourné (ADR-018). Un tour purement
conversationnel ne crée ni branche ni commit.

**Coût** : `llm_max_budget_usd` borne *un appel*. Une conversation a son propre
plafond, `chat_max_conversation_usd` (défaut 2 USD), et son total cumulé est
affiché dans l'UI.

## OrchestratorEvents (WebSocket)

Dès la connexion, le serveur envoie un instantané du run (`RunActif`) :
- `ticket_id` et `ticket_titre` — permettent à la Supervision et à l'en-tête 
  du run d'afficher ces informations sans ouvrir le projet (ticket-286)
- `db_run_id` — identifiant du run en base SQLite, qui permet au frontend de 
  charger l'historique des événements enregistrés lors d'un rechargement 
  (ticket-325)
- `etapes_en_cours: string[]` — liste toutes les étapes actuellement en cours 
  d'exécution (ticket-289). Après l'audit sécurité, reviewer et validateur 
  peuvent tourner en parallèle : le client affiche les deux pastilles actives.

Quand `etapes_en_cours` ou `db_run_id` sont absents (runs lancés avant ces 
additions), les clients replient respectivement sur le champ `etape` et ne 
rechargent pas automatiquement l'historique enregistré.

Tout événement `ticket_status_changed` porte `ticket_titre` dès réception (ticket-324). Pour chaque ticket,
le titre est lu une seule fois du disque ; les événements ultérieurs sur le même ticket portent ce titre en cache,
économisant une lecture par événement.

Ensuite, les clients reçoivent des `OrchestratorEvent` au format JSON :

```json
{
  "type": "agent_started | agent_token | agent_tool_use | agent_done | branch_created |
           ticket_status_changed | test_result | security_audit_started |
           security_audit_done | validation_started | validation_done | 
           documentation_started | doc_updated | livraison_started | 
           run_closed | ci_merge_done | commit_created | pipeline_done | error",
  "agent": "codeur | reviewer | testeur | securite | validateur | doc-technique | doc-fonctionnelle | null",
  "ticket_id": "ticket-007",
  "data": { "round": 1, "token": "def foo", "status": "in-progress", "approved": true },
  "timestamp": "2026-06-20T14:30:00Z"
}
```

## Optimisation du streaming frontend (ticket-353)

Le streaming des tokens peut générer des centaines d'événements par seconde. Pour éviter que l'interface ralentisse, trois optimisations sont appliquées au frontend :

1. **Séparation des tokens** : `agent_token` ne va plus dans `events` ni `ticketEvents`. Le texte s'accumule dans `entries[…].tokens` comme avant. Les consommateurs d'événements lisent seulement les événements de contrôle (`pipeline_done`, `run_closed`, `queue_progress`, `pipeline_start`).

2. **Borne des événements** : au-delà de `MAX_EVENTS = 2000`, les plus anciens sont retirés pour préserver la mémoire. Les événements de contrôle sont **toujours conservés**, même au-delà du plafond, pour que les jalons du pipeline restent visibles dans l'historique.

3. **Regroupement par frame** : dans `useSupervision`, les messages WebSocket reçus sont mis en file et appliqués ensemble une fois par `requestAnimationFrame` (repli sur `setTimeout(…, 16)` hors navigateur), en un seul `setEtats` et un seul `setRuns` par lot. L'ordre d'application reste celui de réception. Un `snapshot` vide d'abord la file en attente avant d'appliquer l'état de référence.

Ces trois changements réduisent les rendus de plusieurs centaines par seconde à **un seul** par cycle d'image, tout en préservant la cohérence de l'état et la traçabilité des événements critiques.


## Chargement dynamique du frontend (ticket-355)

Monaco et les composants centraux du panel d'édition (`Editor`, `DiffView`, `StatsView`, `ChatPanel`) ne sont plus chargés au démarrage global de l'application. Chacun utilise `React.lazy()` et `Suspense` pour se charger à la demande — la première ouverture du composant déclenche le chargement de son code source, pendant qu'un état de chargement sobre s'affiche (`zinc`, ADR-026).

La configuration de Monaco (`MonacoEnvironment`, `loader.config`, workers) s'initialise dynamiquement lors du premier rendu de l'éditeur, non lors du boot de l'application. Vite isole `monaco-editor` dans son propre chunk via `build.rollupOptions.output.manualChunks`, réduisant la taille du bundle initial et permettant au navigateur de l'ignorer jusqu'à sa première utilisation.

## Agents disponibles

| Rôle | Modèle | Usage |
|------|--------|-------|
| `codeur` | claude-sonnet-5-5 | Implémente les tickets feat/fix |
| `reviewer` | claude-sonnet-5-5 | Valide le code produit |
| `orchestrateur` | claude-sonnet-5-5 | Décompose les tickets complexes |
| `architect` | claude-sonnet-5-5 | Analyse architecturale |
| `project-creator` | claude-sonnet-5-5 | Crée de nouveaux projets |
| `github-sync` | — (pas de LLM) | Synchronise GitHub Issues → tickets |

**Skills fournis par défaut** : `codeur` et `architect` chargent `tessera:design-ui` au démarrage, qui impose une charte visuelle (couleurs, typographie, espacement) et les règles de l'ADR-026 à toute création d'interface.

## Communication inter-agents

Les agents ne se parlent pas directement.
L'Orchestrateur :
1. Passe le résultat du Codeur comme contexte au Reviewer
2. Injecte les feedbacks reviewer précédents dans le contexte du Codeur (tour suivant)
3. Décide du routing selon le verdict (`APPROVED` / `CHANGES_REQUESTED`)
4. Logue chaque transition dans `projects/{id}/memory/pipeline-log.md`
5. Persiste chaque run et event dans SQLite

## Mémoire des projets

```
projects/{project_id}/memory/
  decisions.md      ← ADRs, décisions d'architecture
  stack.md          ← versions, commandes, ports
  pipeline-log.md   ← historique des pipelines (auto-généré par l'Orchestrateur)
```

## Ajout d'un nouveau type d'agent

1. Créer `agents/prompts/{role}.md` avec le system prompt
2. Ajouter l'entrée dans `projects/{project_id}/agents.json`
3. Ajouter le role dans l'enum `AgentRole` (`models/agent.py`)
4. Si pipeline custom : modifier `Orchestrator.run_pipeline()`

Pas besoin de modifier le reste du code.

---

## Schéma d'ensemble

```
┌─────────────────────────────────────┐
│      ✅ Tauri v2 Shell (Rust)       │
│  ┌─────────────────────────────┐    │
│  │  ✅ React UI (TypeScript)   │    │
│  │  Monaco · Ticket Board      │    │
│  │  Agent Stream · Sidebar     │    │
│  └──────────────┬──────────────┘    │
└─────────────────┼───────────────────┘
               │ HTTP / WebSocket
┌──────────────▼──────────────────────┐
│     Orchestrateur (FastAPI)         │
│                                     │
│  ┌─────────────┐  ┌───────────────┐ │
│  │  Routers    │  │   Services    │ │
│  │  projects   │  │  AgentRunner  │ │
│  │  tickets    │  │  Orchestrator │ │
│  │  agents     │  │  AgentRegistry│ │
│  │  agent_adm  │  │  Planner      │ │
│  │  orchestr.  │  │  GitClone     │ │
│  └─────────────┘  └───────┬───────┘ │
└──────────────────────────-┼─────────┘
                            │ Anthropic SDK
                    ┌───────▼───────┐
                    │  Claude API   │
                    │ (Sonnet 4.6 / │
                    │  Haiku 4.5)   │
                    └───────────────┘
                            │
               Filesystem (tickets/memory/)
               GitHub API (issues/PRs/clone)
```

### Flux d'un ticket

```
POST /orchestrator/run { project_id, ticket_id }
        │
        ├─ git checkout -b ticket-XXX-slug   (forkée de la ref de base)
        │
        ├─ Codeur (Claude) ──streaming──▶ WS /orchestrator/stream
        │       ↓ écrit réellement les fichiers
        ├─ git diff  →  c'est CE diff que relisent les agents suivants
        │
        ├─ Testeur            → exécute la suite de tests du projet
        ├─ Sécurité (OWASP)   → BLOCK si CRITICAL/HIGH  →  ticket → blocked/
        ├─ Reviewer (Claude)
        │       ↓ CHANGES_REQUESTED  →  retour Codeur (max 3 tours)
        │       ↓ APPROVED
        ├─ Validateur         → vérifie les critères d'acceptation un par un
        ├─ Doc-updater        → met à jour README / docs / CLAUDE.md
        │
        ├─ git commit
        │       ↓ approuvé      →  "<type>: ticket-XXX — <titre>"  + ref de base avancée
        │       ↓ non approuvé  →  "chore: ticket-XXX — unapproved work (<raison>)"
        │
        └─ PipelineResult { approved, rounds, final_status, branch, commit_sha }
```

> Quel que soit le verdict, le travail du codeur est commité sur la branche du
> ticket : rien n'est perdu, et l'arbre de travail reste propre pour le ticket
> suivant. Seul un ticket **approuvé** fait avancer la ref de base, de sorte
> qu'un plan de tickets séquentiels s'empile correctement sans jamais hériter
> du travail rejeté d'un ticket précédent.
## Design et maquettes

Chaque projet peut déclarer une maquette d'interface validée dans `design/maquette/` (fichiers `.dc.html` exportés depuis l'éditeur Claude Design). Quand la maquette existe, elle fait autorité pour :

- **Structure** : ordre des composants, hiérarchie visuelle
- **Espacements** : tailles, marges, padding
- **États** : hover, focus, disabled, et autres variantes
- **Couleurs** : chaque teinte définie dans la maquette devient un token de la charte CSS (`memory/design.md`)

Les textes affichés dans la maquette sont des données fictives, jamais du contenu à recopier. Les agents (codeur en premier, reviewer en validation) reproduisent d'abord la structure et les espacements de la maquette, puis y appliquent la charte de couleurs et typographie.

Le gabarit `fastapi-react` inclut un dossier `design/maquette/` avec un `README.md` qui explique ce rôle. Les nouveaux projets créés depuis ce gabarit ont donc la structure prête.

## Mise en ligne (ADR-053, ticket-463)

> Conçue, pas encore construite : les tickets 464 à 472 la réalisent.

Tessera crée et relie les ressources en ligne d'un projet — Vercel, base de
données, Resend, Stripe, DNS Cloudflare — sur une **action explicite de
l'utilisateur** (`POST /api/v1/projects/{id}/provision`, puis un bouton « Mettre
en ligne »). Aucun agent du pipeline ne la lance, et aucun outil d'agent ne
l'expose.

### Garde des jetons

- Les jetons (`VERCEL_TOKEN`, `NEON_API_KEY`, `RESEND_API_KEY`,
  `STRIPE_API_KEY`, `CLOUDFLARE_API_TOKEN`) se lisent dans le `.env` de Tessera,
  par le backend seul (`config.Settings`). Ils ne sont jamais transmis à un
  sous-processus agent : `agent_sdk` les vide dans l'environnement du CLI, comme
  `ANTHROPIC_API_KEY`.
- Un hook `PreToolUse` refuse à `Read`, `Glob`, `Grep` et `Bash` le `.env` de
  Tessera (le chemin de `Settings.env_file`). Comme le contrôle d'écriture
  d'ADR-031, il attrape une erreur, pas une évasion : le vrai plafond d'un jeton
  est sa portée, pas ce hook.
- Un secret reçu d'une API (clé Resend, `whsec_…` Stripe, URL de base) passe
  **d'une API à l'autre** : il est écrit dans une variable Vercel de type
  `sensitive` et n'est ni stocké, ni loggé, ni renvoyé. Les événements de la
  mise en ligne ne portent que des noms d'étapes et des états.
- Le masquage des logs porte sur les valeurs des jetons configurés et sur tout
  secret reçu pendant l'appel. Une erreur de service se réduit au statut HTTP et
  au code d'erreur de l'API, jamais à son corps (qui peut répéter la valeur).
- La porte de push (ADR-048) traite les valeurs des jetons configurés comme des
  termes interdits : un jeton ajouté dans un diff arrête le push.

Cinq jetons gèrent l'accès aux services de mise en ligne : `VERCEL_TOKEN`, `NEON_API_KEY`, `RESEND_API_KEY`, `STRIPE_API_KEY`, `CLOUDFLARE_API_TOKEN`. Chacun est un champ `SecretStr` dans `config.Settings`, vide par défaut.

Le backend seul les lit et les stocke. Aucun agent ne les reçoit, aucun log ne les montre, aucun push ne les emporte. Les valeurs sont masquées dans les logs par `SecretRegistry`, et l'agent SDK vide ces variables de son environnement avant chaque appel.

Un hook `PreToolUse` refuse les outils `Read`, `Glob`, `Grep` et `Bash` qui tenteraient d'accéder au `.env` de Tessera (à la racine du dépôt). Pour `Bash`, le repérage lexical détecte les chemins ; il attrape une erreur, pas une évasion — voir ADR-031.

**Portée minimale et expiration** : chaque jeton doit être créé avec les permissions strictement nécessaires à son service (déployer pour Vercel, migrer pour Neon, etc.) et configuré avec une date d'expiration — la plupart des fournisseurs la supportent. Sans expiration, les jetons entrent dans `FORBIDDEN_TERMS` au moment du push, et le diff s'arrête si la valeur y apparaît (ADR-048, ADR-050).

### Portée minimale

| Service | Jeton | Limite |
|---|---|---|
| Stripe | clé restreinte | produits, prix, webhooks en écriture ; **mode test** par défaut |
| Vercel | jeton de compte | expiration obligatoire ; équipe limitée au scope du compte |
| Cloudflare | jeton d'API | `Zone.DNS` en édition, sur la seule zone du projet |
| Resend | clé d'API | création de domaines et de clés d'envoi |
| Neon | clé d'API | projets du compte |

Le mode réel de Stripe n'est jamais activé par Tessera : il suppose une clé
restreinte `live`, posée à la main, et une déclaration explicite
(`"stripe": {"mode": "live"}`).

### Déclaration par projet

Dans `agents.json`, un bloc `online` (distinct de `services`, qui désigne les
commandes locales d'ADR-042) ; `agents.json` reste interdit en écriture aux
agents (ADR-027) :

```json
"online": {
  "domain": "pronosti.fr",
  "resources": ["vercel", "database", "resend", "dns", "stripe"],
  "stripe": {
    "webhook_path": "/api/stripe/webhook",
    "events": ["checkout.session.completed"],
    "product": "Publication d'un événement",
    "price_cents": 990
  }
}
```

`webhook_path` et `events` sont obligatoires dès que `stripe` est listé : les
événements dépendent du code du projet, Tessera ne les devine pas.
`product` et `price_cents` sont facultatifs — un projet qui passe son prix en
ligne à Stripe n'a besoin ni de l'un ni de l'autre.

Absent : pas de bouton, pas d'endpoint utile. Une ressource non listée n'est ni
créée ni contrôlée. Le nom du projet Vercel, de la base et de la clé Resend est
l'identifiant du projet.

### Étapes, dans l'ordre

1. **Projet Vercel** : trouvé par son nom, sinon créé et relié au dépôt
   `github_remote` ; le domaine est ajouté au projet.
2. **Base** : projet Neon trouvé par son nom, sinon créé ; `DATABASE_URL`
   écrite dans Vercel. Sans `NEON_API_KEY` (compte géré par l'intégration
   Vercel), l'étape passe `manual` : elle vérifie seulement que `DATABASE_URL`
   existe dans Vercel.
3. **Variables** : celles que Tessera sait produire (`NEXT_PUBLIC_APP_URL`,
   `SESSION_SECRET`, `CRON_SECRET` générés), posées **seulement si absentes**.
4. **Domaine Resend** : trouvé ou créé ; ses enregistrements DNS sont
   collectés, une clé d'envoi dédiée est créée et écrite dans Vercel.
5. **DNS** : les enregistrements demandés par Vercel et Resend sont publiés
   dans la zone Cloudflare. Sans Cloudflare déclaré, ils sont listés pour
   l'utilisateur (`manual`).
6. **Vérification Resend** : déclenchée après les DNS ; `pending` n'est pas un
   échec, une relance la relit.
7. **Stripe** : produit (trouvé par `metadata.tessera_project`) et prix (par
   `lookup_key`) s'ils sont déclarés, webhook (par URL) toujours ; le secret du
   webhook va dans Vercel.
8. **Redéploiement** : seulement si une variable a été écrite pendant la
   relance.

### Reprise et idempotence

Aucun état local n'est écrit : **le monde est la source de vérité**. Chaque
relance lit d'abord chaque service (`inspect`), puis ne crée que ce qui
manque (`apply`). Une variable Vercel `sensitive` ne se relit pas : on n'en
contrôle que le nom, et on n'écrase jamais une valeur existante.

Une ressource trouvée en double refuse l'étape. Un secret qui n'est montré
qu'à la création (clé Resend, `whsec_…`) trouvé **sans** sa variable Vercel est
perdu : l'étape s'arrête en `needs_human` et nomme la ressource à supprimer
dans le tableau de bord, puis la relance la recrée. Tessera ne supprime jamais.
Une étape en échec arrête les suivantes ; les étapes déjà faites restent faites.

### Ce qui reste humain

Création des comptes, achat du domaine, activation du mode réel Stripe, et la
clé Stripe du **site** : l'API Stripe ne crée pas de clé, `STRIPE_SECRET_KEY`
du projet se pose donc à la main dans Vercel. Tessera en vérifie le nom
(`needs_human` s'il manque), jamais la valeur.

### Observation

Chaque étape émet `provisioning_step` (`nom`, `etat` : `done`, `skipped`,
`pending`, `manual`, `needs_human`, `failed` ; `todo` en lecture seule) sur le canal d'ADR-041. Un
verrou par projet, distinct de `RunLock` (la mise en ligne ne touche pas à
l'arbre), refuse une seconde mise en ligne simultanée avec un 409.

### Endpoints de provisioning

Les deux points d'entrée HTTP du plan :

- **`POST /api/v1/projects/{project_id}/provision`** : déclenche le plan en tâche de fond. Répond `202` sans attendre. Le plan s'observe sur `WS /api/v1/orchestrator/observe` (ADR-041). L'authentification exige `STATIC_TOKEN` si elle est renseignée.
- **`GET /api/v1/projects/{project_id}/provision`** : lit l'état du plan via `dry_run=True` — chaque étape appelle `inspect`, aucune `apply`. Utile pour vérifier l'état sans risque.

Le verrou de mise en ligne est distinct de `RunLock` : le même projet ne peut pas lancer deux provisioning en même temps. Une étape qui lève une exception libère le verrou et devient un événement `failed`. La réponse HTTP ne porte aucune trace d'appel ni de jeton (ADR-053).

Aucun module du pipeline (routers, services d'orchestration), du chat ni des agents n'importe `services.provisioning` : le provisioning reste isolé et utile seulement à l'utilisateur.

### Moteur de provisioning (ticket-465)

Package `services/provisioning/` : orchestrateur des étapes de mise en ligne, exécutées dans l'ordre déclaré dans le bloc `online` d'`agents.json`.

**Principes généraux**

- Aucun fichier d'état : le **monde est la source de vérité**. Les services eux-mêmes (via leurs API publiques) disent ce qui existe. Chaque relaunch relit tout.
- Chaque étape lit d'abord (`inspect`) pour déterminer s'il faut agir, puis crée le manquant (`apply`).
- Un échec (`failed`) ou demande d'intervention humaine (`needs_human`) arrête la suite sans annuler ce qui est déjà fait : idempotence garantie.

**Architecture**

- `StepState` (enum) : `todo`, `done`, `skipped`, `pending`, `manual`, `needs_human`, `failed`
- `StepResult` : état + détail (nom de ressource, instruction — jamais un secret)
- `ProvisioningStep` (Protocol) :
  - `name` — identifiant unique
  - `inspect(ctx)` — lit le monde, retourne un `StepResult` (lecture seule)
  - `apply(ctx)` — crée ce qui manque (jamais appelé en `dry_run`)
- `ProvisioningContext` : paramètres partagés (project_id, OnlineConfig, env_writer, DNS voulu, envs modifiés, DNS publié)
- `OnlineConfig` (Pydantic v2) : lit le bloc `online` d'`agents.json` (domaine, ressources, configuration Stripe)
- `ProvisioningPlan.run(ctx, dry_run)` :
  - `dry_run = true` → rend `todo` pour ce qui manque, n'appelle jamais `apply`
  - Si `skipped` → passe à la suivante
  - Sinon : appelle `apply`, continue
  - Si `failed` ou `needs_human` → arrête les suivantes (laisse au statut `todo`)
- `ServiceError(service, status, code)` : message limité au statut HTTP et au code d'erreur de l'API, jamais le corps de la réponse (qui peut contenir un secret)

**Observation**

Chaque appel à `inspect` ou `apply` émet un événement `provisioning_step` sur le WebSocket (ADR-041) :

- `step` — nom de l'étape
- `state` — le StepState obtenu
- `detail` — instruction ou nom de ressource créée
- **Invariant** : aucun secret du registre (`SecretRegistry`, ticket-464) ne figure dans `detail`

**Branchement des services**

Les tickets 466–470 implémentent chacun un `ProvisioningStep` pour un service (domaine, DNS, email, paiement…) et s'y branchent.

### Client Vercel (ticket-466)

Trois étapes coordonnées pour provisionner un projet Vercel :

1. **`vercel_project`** : trouve ou crée un projet par son nom, ajoute le domaine s'il manque, et verse les enregistrements DNS attendus dans `ctx.wanted_dns`.
2. **`variables`** : pose les variables d'environnement (`NEXT_PUBLIC_APP_URL`, `SESSION_SECRET`, `CRON_SECRET`) si elles sont absentes, en type `sensitive` sauf la variable publique. **Aucune variable existante n'est jamais réécrite** — c'est une garantie de sécurité (ADR-053).
3. **`redeploy`** : redéploie le dernier déploiement si une variable a été écrite (si `ctx.changed_env` n'est pas vide).

Idempotence garantie : rejouer le passage ne change rien si le projet, le domaine et les variables sont déjà en place. Les jetons et valeurs sensibles ne sont jamais loggés ni inclus dans les erreurs.

### Étapes Resend (ticket-468)

Deux étapes de configuration du domaine d'envoi dans l'API Resend, servant à la livraison des e-mails transactionnels.

**`resend_domain`** : cherche ou crée un domaine d'envoi dans Resend. À la création, l'API retourne ses enregistrements DNS (DKIM, SPF, DMARC) que l'étape range dans `ctx.wanted_dns` pour que le DNS soit publié avant vérification. Crée aussi une clé d'API limitée au domaine seul, nommée d'après le projet, et l'écrit dans Vercel sous `RESEND_API_KEY`. Idempotente : un domaine existant n'est pas recréé. Cas particulier : si une clé existe sans variable Vercel, l'étape rend `needs_human`, nomme la clé à supprimer, et n'émet aucun appel de suppression.

**`resend_verify`** : après publication du DNS, lance la vérification du domaine (`POST /domains/{id}/verify`). N'agit que si `ctx.dns_published` est vrai. Les statuts du domaine rendent : `verified` → `done`, en attente → `pending`, `failed` → `failed`.

L'ordre global est : domaine créé et enregistrements récupérés, DNS publié (ticket-469), puis vérification lancée. Dépend de ticket-466 (Vercel) et ticket-469 (DNS).
### Client Neon (ticket-467)

Le client Neon crée ou cherche un projet PostgreSQL chez Neon via l'API `https://api.neon.tech`. Localisation : `services/provisioning/neon.py`.

Même discipline d'erreurs et de logs que le client Vercel. Trois opérations :
1. **Chercher** un projet par nom (identifiant du projet)
2. **Créer** s'il n'existe pas
3. **Lire l'URI** de connexion et la passer à `env_writer.set_env("DATABASE_URL", …)` pour inscription dans `SecretRegistry`

L'URI de connexion n'apparaît jamais dans les logs, les événements, ni dans le corps d'une `ServiceError`. Seul le statut de l'opération est rapporté.

La docstring cite les pages de documentation Neon : projets, branches, URI de connexion.

### Étape database (ticket-467)

L'étape `database` du provisioning assure qu'un projet a une base de données PostgreSQL chez Neon et que `DATABASE_URL` est inscrit dans Vercel.

Flux :
1. Vérifier si `DATABASE_URL` existe dans Vercel
2. Si oui → retour `skipped`, sans appel à Neon
3. Si non, chercher un projet Neon portant le nom du projet Tessera
4. Si trouvé → lire l'URI ; si absent → créer, puis lire l'URI
5. Écrire `DATABASE_URL` dans Vercel → retour `done`

Cas particuliers :
- **Deux projets Neon portent le même nom** → collision détectée, rien n'est créé, retour `failed`
- **`NEON_API_KEY` vide** (clef API non renseignée) :
  - `DATABASE_URL` existe dans Vercel → retour `manual` (base fournie manuellement)
  - `DATABASE_URL` n'existe pas → retour `needs_human` avec instruction d'en fournir une ou de renseigner `NEON_API_KEY`

L'idempotence est garantie : un relancement immédiat ou après redémarrage retrouve la même base et ne la recrée pas.

L'étape ne supprime jamais de base, ne migre pas de schéma — c'est du ressort du projet lors de son déploiement.


### Client Cloudflare (ticket-469)

Gère les enregistrements DNS de la zone du projet. Le jeton `CLOUDFLARE_API_TOKEN` est limité à `Zone.DNS` en édition sur la seule zone du projet (ADR-053).

La zone est identifiée via `online.domain` dans la configuration de mise en ligne. L'achat du domaine et son ajout à Cloudflare restent humains. Les enregistrements DNS sont publics : leur nom, type et contenu peuvent être documentés sans restriction d'accès.

### Étape DNS (ticket-469)

Publie dans la zone Cloudflare les enregistrements demandés par les étapes antérieures (Vercel, Resend), listés dans `ctx.wanted_dns`.

**Comportement** :
- Chaque enregistrement est créé s'il n'existe pas à l'identique (type, nom, contenu)
- Les enregistrements identiques sont ignorés
- Aucun enregistrement n'est jamais modifié ou supprimé (pas d'appel DELETE)
- Deux enregistrements de même type et nom mais contenu différent déclenchent `needs_human` ; l'étape n'effectue aucune écriture

**Résultats possibles** :
- Succès : tous les enregistrements demandés existent (`ctx.dns_published = true`)
- `needs_human` : conflit détecté (même type/nom, contenu différent)
- `manual` : `CLOUDFLARE_API_TOKEN` absent ou `dns` non déclaré dans `online.resources` ; l'étape liste les enregistrements à ajouter manuellement

