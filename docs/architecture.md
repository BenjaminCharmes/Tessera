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

### Couche git (ADR-018, ADR-024, ADR-027)

`GitWorkspaceService` isole les opérations git du pipeline, et ne s'applique
**jamais** au dépôt de Tessera lui-même — uniquement au projet ciblé.

Cette promesse a demandé sept correctifs, tous nés d'un usage réel :

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

Un run dont le commit **échoue** ne peut pas s'annoncer approuvé : le ticket
passe `blocked` et la raison est émise. « Rien à committer » reste un succès, et
s'en distingue.

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
production, sécurité, revue, validation, documentation, livraison — en tête du panneau 
Agents. Chaque pastille représente une étape, avec trois états : faite (`green`), en cours 
(`blue`), à venir (`zinc`). Une étape désactivée pour le projet n'a pas de pastille. Un 
refus de l'audit sécurité ou une validation rejetée passent la pastille correspondante en 
`red`. 

Après l'audit sécurité, reviewer et validateur peuvent tourner en parallèle (ticket-289) :
`StageStrip` marque `active` toute étape présente dans `etapesEnCours`, permettant 
d'afficher deux pastilles `blue` au même moment. Une étape n'est `done` que si son 
événement de fin a été reçu, ou si une étape qui la suit (et ne tourne pas en parallèle) 
a démarré.

`coherence.test.ts` verrouille les trois règles : il lit les sources et échoue
à la première réintroduction d'une couleur bannie, d'une taille de texte
arbitraire ou d'un glyphe utilisé comme affordance.

Ce système est imposé aux agents créant une interface via le skill `tessera:design-ui`, chargé par défaut par le codeur et l'architect : toute UI doit partir d'une charte déclarée (couleurs, typographie, espacement), et n'en sortir sur aucune valeur.

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

## Visualisation des runs terminés (ticket-280, ticket-281)

Un run qui quitte la supervision — fermé ou au redémarrage du backend — disparaît 
de la WebSocket temps réel. Les événements persistent en SQLite, et l'utilisateur 
peut les rejouer depuis l'historique :

1. **Récupération** : un clic sur une ligne de `RecentRuns` appelle l'endpoint 
   du ticket-280 avec l'identifiant du run, qui retourne l'ensemble de ses 
   événements, du début à la fin.
2. **Rejeu** : le frontend applique chaque événement dans `applyEvent` — le même 
   code que pour la WebSocket temps réel. L'état visuel se reconstruit entièrement 
   en quelques millisecondes, cartes comprises.
3. **Lecture seule** : la vue rouverte n'affiche ni bouton d'arrêt, ni champ de 
   message, ni chrono qui tourne. C'est un instantané interactif du passé, pas 
   un run vivant.

Cette capacité de rejeu repose sur le fait que chaque événement porte assez 
d'information pour reconstituer l'état. Les `OrchestratorEvent` — écrits 
initialement pour le temps réel — le satisfont aussi bien pour l'historique : 
c'est la même sérialisation JSON, les mêmes champs, aucune adaptation.


## Gestion des événements en file (ticket-313)

Un mode file traite plusieurs tickets en séquence. Le pipeline enregistre l'historique complet de tous les événements (Pipeline log, SQLite) pour l'audit et la traçabilité. Mais côté interface, **chaque ticket affiche son propre état d'étapes**, vierge au démarrage.

À chaque nouveau ticket (`queue_progress`), les événements du ticket courant repartent de zéro :

- Les pastilles de `StageStrip` reflètent l'état du ticket **en cours**
- Le ticket suivant démarre avec une bande d'étapes vierge (production à faire, sécurité à venir, etc.)
- Le Pipeline log accumule tous les événements de tous les tickets et reste complet

### Rejouer un run fermé sans dupliquer le texte

Quand un utilisateur revient à un run depuis la Supervision, le serveur rejoue le contenu textuel accumulé. Un aller-retour entre deux runs recevrait le même rejeu deux fois. Pour prévenir une duplication visible, le client traite les événements replayed de manière à garder une trace fidèle du texte — ni doublon, ni perte.

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

Dès la connexion, le serveur envoie un instantané du run (`RunActif`), qui porte `ticket_id` et `ticket_titre`, permettant à la Supervision et à l'en-tête du run d'afficher ces informations sans ouvrir le projet (ticket-286). L'instantané contient désormais `etapes_en_cours: string[]`, qui liste toutes les étapes actuellement en cours d'exécution (ticket-289). Après l'audit sécurité, reviewer et validateur peuvent tourner en parallèle : le client affiche les deux pastilles actives. Quand `etapes_en_cours` est absent (run ancien), les clients replient sur le champ `etape`.

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
