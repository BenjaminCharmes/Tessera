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

### Reprise de runs orphelins (ticket-369)

Au démarrage du backend, après la solidification des runs orphelins en base (`solder_les_runs_orphelins`, ticket-177), une étape remet les dépôts en état quand un arrêt les a laissés sales pendant un run.

Pour chaque run interrompu, si la copie de travail du projet est restée sur une branche `<ticket_id>-…` :

1. Les changements non committés sont committés avec le message du pipeline non approuvé, ce qui garantit que l'arbre n'est jamais sale entre deux runs (ADR-018)
2. La fiche de ticket est remise en `todo` si elle était en `in-progress` ou `in-review`
3. La copie de travail revient sur la branche de base du projet

Si la copie de travail est sur une autre branche, aucune action n'est prise. Les erreurs git durant cette reprise sont loggées sans exception : un problème au redémarrage ne doit jamais bloquer le backend.

### Intégrité de la fiche lors de la reprise (ticket-377)

Quand une branche de ticket est reprise au démarrage, sa fiche est validée. Si le ticket a été déplacé de `tickets/todo/` vers `tickets/in-progress/` ou `tickets/in-review/` mais que ce déplacement n'a pas été committé (fichier non suivi), la reprise ajoute explicitement le fichier au commit « unapproved work ». Seule la fiche du ticket est ajoutée ; aucun autre fichier non suivi ne peut y entrer.

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

## Gestion des limites de session

Quand l'abonnement Claude atteint sa limite horaire, le CLI répond : « You've hit your session limit · resets <heure> ». Avant, le pipeline traitait cette erreur comme toute exception : le ticket passait en `blocked`, bloquant le projet.

Depuis le ticket-388, une erreur de limite de session provoque :
1. Le ticket en cours repasse en `todo` (son travail reste commité comme non approuvé)
2. La file s'arrête **avant** le ticket suivant
3. Un événement est émis portant `session_limit` comme raison et l'heure de reprise
4. Un log dans `memory/pipeline-log.md` : `[<projet>] file interrompue : limite de session (reprise : <heure>)`

Contrairement à `blocked`, `todo` ne bloque pas le projet. La file peut reprendre après l'heure indiquée. Aucun ticket n'est abîmé.

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
