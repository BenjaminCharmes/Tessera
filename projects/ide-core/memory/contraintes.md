# Contraintes en vigueur

Règles en vigueur, chacune avec son ADR ; leur histoire est dans
`decisions.md`.

---

## Proposées

Cette section n'est injectée dans aucun appel d'agent. Une règle nouvelle
s'écrit ici, avec son ADR ; un humain l'accepte en la déplaçant dans sa
section. (ADR-055)

- **Avec `worktree.compte_agent` et `AGENT_USER`, la commande de test et l'app du contrôle visuel partent aussi sous ce compte** ; tout échec de lancement est une panne d'environnement, jamais un repli sous le compte du backend. (ADR-085, ADR-083, ADR-037) — *à accepter quand `AGENT_USER` sera renseigné sur un projet.*
- **Sous `AGENT_USER`, le CLI d'un agent part sous ce compte, environnement bâti de zéro** ; tout échec → `ProviderIndisponible`, jamais de repli sous le compte du backend. (ADR-083, ADR-037) — *à accepter quand `AGENT_USER` sera renseigné sur un projet : d'ici là, aucun agent ne la rencontre.*

## Git et périmètre d'écriture

- **Un projet qui déclare `worktree` exécute chaque run dans son worktree,
  jamais dans le checkout.** Sous `IDE_WORKTREES_DIR/<projet>/<ticket>`,
  depuis `origin/<base>` : la racine d'écriture du run, sans session humaine.
  (ADR-056)
- **Un lien de `populate` ne vise que ce que git ignore, et se retire avant
  toute suppression récursive.** Ce qui s'édite se copie. Jamais le `.env` de
  Tessera ; une entrée absente se journalise sans bloquer. (ADR-056, ADR-053)
- **Ne jamais écrire hors de la racine d'écriture du run** — le projet, son
  worktree (ADR-056) ou le dépôt ancêtre si `git_root: ancestor`. Un hook
  `PreToolUse` bloque ailleurs `Write`, `Edit`, `NotebookEdit` et les
  redirections Bash simples. Lire hors du projet reste permis, sauf le `.env`
  de Tessera. (ADR-031, ADR-053)
- **Le service de documentation n'écrit dans `agents.json` que la clé
  `description`**, proposée par doc-technique et contrôlée. (ADR-068,
  ADR-027, ADR-057)
- **Ne jamais émettre une commande git ou `gh` en écriture.** Le hook
  `PreToolUse` n'admet que des lectures nommées (liste blanche). `agents.json`, `.git/`,
  `.claude/settings*.json` et `.github/workflows/` se refusent en écriture.
  (ADR-067, ADR-027)
- **Le script que `test_command` lance se refuse en écriture**, comme
  `agents.json`. Un diff qui touche la configuration des tests (`conftest.py`,
  `[tool.pytest*]`, `[tool.mypy]`, `vite.config.*`, `vitest.*`, `eslint.config.*`,
  `tsconfig*.json`, `scripts` de `package.json`…) sans que le ticket la nomme par
  son chemin complet est refusé à la revue. (ADR-027, ADR-072)
- **Une règle nouvelle s'écrit sous `## Proposées` dans `contraintes.md`,
  avec son ADR.** Un diff qui modifie ce fichier ailleurs met le run en
  `blocked` : un humain accepte la règle en la déplaçant dans sa section.
  (ADR-055)
- **Une leçon s'écrit sous `## Proposées` de `memory/lecons.md`, par le
  service seul.** Seule `## En vigueur`, où un humain la déplace, atteint
  codeur et reviewer. Un diff de run qui touche ce fichier met le run en
  `blocked`. (ADR-074, ADR-055)
- **Avant toute création de branche, `git rev-parse --show-toplevel` doit
  renvoyer le dossier du projet**, sinon `NotAGitRepository`, sauf
  `git_root: ancestor`. (ADR-024, ADR-028)

## Livraison et autonomie

- **Chaque run, et le chat (`chat-<horodatage>`), a sa branche et finit par
  un commit** : approuvé, type du ticket ; sinon `chore: … — unapproved work
  (…)`. L'arbre ne reste jamais sale. (ADR-018, ADR-019)
- **Ne jamais forcer un push** : un refus est une information. (ADR-022)
- **Déclarer le niveau d'autonomie dans `agents.json`** (`autonomy:
  commit | pr | merge`, défaut : `commit`). Merge sur CI verte seulement,
  sauf `merge_without_ci: true`. (ADR-029, ADR-045)
- **Une approbation vaut pour un commit précis.** Avant le push, seuls des
  commits de rangement (`tickets/**`, `memory/pipeline-log.md`) peuvent suivre
  `approved_sha`, sinon `blocked` sans push. `CIWatcher` ne merge qu'une PR dont
  la tête relue est encore `pushed_sha`, merge lié à ce SHA ; sinon `blocked`,
  PR ouverte. (ADR-039)
- **Un run non approuvé ne se livre jamais.** Les exceptions de livraison
  restent dans `Livraison.arret` et ne font pas échouer le run. (ADR-030)
- **Sur un conflit de rebase, `resolveur-conflit` tente.** Une résolution
  qui aboutit ouvre sa PR, jamais mergée seule, même en `merge`. Tout doute annule tout. (ADR-033)
- **La phase 1 de livraison (rebase, push, PR) libère le verrou du
  projet.** La phase 2 (attente CI, merge) tourne dans `CIWatcher`.
  `depends_on` bloque le ticket suivant jusqu'au merge. Une CI rouge met le
  ticket en `blocked`, PR ouverte, sans relance. (ADR-051)
- **Une livraison attend, dans une limite de temps, que les PR du projet
  confiées à `CIWatcher` soient mergées ou bloquées**, pour rebaser dessus.
  (ADR-065, ADR-051)
- **Une PR devenue conflictuelle ne se met à jour que par un merge de la base
  dans sa tête, encore `pushed_sha`, sans push forcé** ; seuls des conflits de
  journaux s'y résolvent, en union, sans agent.
  (ADR-069, ADR-022, ADR-039)

## Portes qui échouent fermées

- **Toute exception en production termine le run en `blocked` avec
  commit.** Jamais une erreur serveur, jamais un arbre sale. (ADR-037)
- **Un worktree qui porte du travail non commité ne se supprime pas** ;
  orphelin au démarrage, il se commite comme un run non approuvé, puis se
  supprime. (ADR-056, ADR-037)
- **Le détecteur d'anomalies observe sans gouverner** : sans LLM, `git` ni
  `gh`, il ne touche à aucun run ni dépôt, et son échec n'atteint aucun run.
  (ADR-078, ADR-037)
- **Un appel d'agent qui change un fichier protégé, un hook ou la config git
  met le run en `blocked`** (empreinte avant/après). (ADR-084, ADR-037)
- **Un projet ne porte qu'un run à la fois** (`RunLock`, 409) ; deux projets
  tournent en parallèle. (ADR-038)
- **L'audit sécurité et le validateur échouent fermés.** Provider
  indisponible, réponse illisible ou exception →
  `BLOCK` / `CHANGES_REQUESTED`. Une faille `CRITICAL` ou `HIGH` bloque
  quel que soit le verdict LLM. (ADR-039)
- **En mode autonome, vérifier dépense estimée et quota réel entre deux
  tickets, jamais au milieu** ; un quota inconnu ne bloque pas. (ADR-020)
- **Une question sans réponse reprend, passé `dialogue_timeout_s`, sur une
  hypothèse énoncée** ; en mode autonome, le délai ne démarre pas. (ADR-025)
- **Le superviseur n'agit que par son registre fermé**, sur une sortie
  validée par schéma, sans outil. Jamais l'argent, une suppression, un secret,
  un projet `professional`, `agents.json`, `.github/`, `CLAUDE.md`, `.git/` ;
  une règle ou leçon touchant une porte va dans « À toi », et sans
  `pipeline.superviseur` déclaré par un humain il n'en décide aucune. (ADR-080)
- **Une intervention du superviseur est un run `supervision`** sous `RunLock`,
  jamais pendant une file : un commit par action, une ligne dans
  `memory/supervision.md`, livrée par `livrer_intervention` (PR seule). Il ne
  merge jamais et ne relance une file qu'une fois par coupure d'infrastructure.
  (ADR-080, ADR-030)
- **`signaler` est le seul chemin d'un agent vers le backlog d'ide-core**
  (projet déduit du run, 3 par run, 1 500 caractères, secret ou terme interdit
  refusé). Une revue de projet est un run `design` borné à `tickets/**` et
  `memory/**` ; un numéro de `prochain_numero.py` est pris dès l'appel. (ADR-080)

## Artefacts et projets

- **Les artefacts Tessera s'excluent via `.git/info/exclude`, jamais via
  `.gitignore`.** (ADR-021)
- **Les artefacts d'un projet cloné ou importé restent `local` par défaut,
  ceux d'un projet créé par l'IDE sont versionnés** ; un autre mode se déclare.
  (ADR-023)
- **Les services d'un projet se déclarent dans `agents.json`
  (`services: [{nom, commande}]`)** ; sans déclaration, pas de bouton. Leur
  lancement survit au redémarrage. (ADR-042, ADR-082)
- **Un run ne lance ni serveur ni capture sans `pipeline.controle_visuel`
  déclaré.** L'app part du worktree du run, sur un port libre, sans tuer de
  processus ; les captures restent hors du dépôt.
  (ADR-062, ADR-042, ADR-021)

## Provider et orchestration

- **Les services passent par `LLMProvider` (`complete`/`stream`), jamais
  par le SDK.** (ADR-017)
- **Chaque rôle déclare `provider`, `model` et `fallback` dans `agents.json`**
  (défaut `agent_sdk`). Le repli ne part
  que sur indisponibilité (`provider_fallback`), run `rapide` ou prompt au-delà
  du `fallback_above_chars` d'un rôle `ollama`, jamais sur une réponse
  illisible. (ADR-046, ADR-059, ADR-071)
- **Un rôle déclaré `"web": true` reçoit `WebFetch` et `WebSearch` et
  perd `Bash`.** (ADR-049)

*(architect, codeur, reviewer)*

- **Un run démarre par `POST /orchestrator/run` et s'observe sur
  `WS /orchestrator/observe`** ; `RunRegistry` tient les runs vivants et leur
  dialogue. (ADR-041)
- **L'orchestrateur est instancié à chaque requête, sans état interne** ;
  `RunLock` et `RunRegistry` vivent hors de lui. (ADR-008)
- **Le verdict du reviewer, de l'audit sécurité et du validateur se lit dans
  une sortie validée par un schéma, jamais dans le texte** ; absente, hors
  schéma ou contradictoire, elle refuse. (ADR-061, ADR-009)
- **Un module de `services/` vit dans son domaine et n'importe que son
  domaine ou un plus bas** (`ORDRE` de `test_domaines_services.py`). Aucun
  paquet de premier niveau hors `models`, `services`, `routers`, `utils`.
  (ADR-076)
- **Seuls les cinq réglages de `reglages.py` se changent depuis l'interface**,
  lus par `reglages.courants()` et figés à l'ouverture d'un run. Écrire exige
  un `Origin` déclaré ; aucun agent n'appelle `/api/v1/reglages`. (ADR-075,
  ADR-031)
- **`role: github-sync` passe par `POST /api/v1/agents/run`**, sans endpoint
  dédié. (ADR-010)

## Confidentialité

- **Aucune donnée professionnelle dans un dépôt personnel** — nom de
  client, e-mail d'employeur, identifiant, jeton, hostname interne — ni
  dans le contenu ni dans les métadonnées git. (ADR-043)
- **Avant tout push, le diff ajouté, les messages et les auteurs passent
  `FORBIDDEN_TERMS`** ; `"confidentiality": "professional"` en exempte un
  projet. (ADR-048)
- **Un secret de Tessera se lit : environnement, coffre du système, puis
  `.env`**. Ni exporté à un sous-processus, ni affiché, ni passé en argument, ni
  donné à un agent ; seule une action de l'utilisateur crée une
  ressource en ligne. Aucun agent n'exécute le coffre (`keyring`, `cmdkey`,
  `coffre_cli`). (ADR-073, ADR-053)
- **Les termes interdits s'arrêtent à trois portes** (push du pipeline, hook
  `pre-push`, CI de chaque PR) ; une porte qui ne peut juger refuse. (ADR-050)
- **Toute requête HTTP ou WebSocket, sauf `/health` et le préflight, exige le jeton de session** (`STATIC_TOKEN` ou tiré au démarrage). (ADR-081, ADR-031)

## Interface et design

*(codeur, reviewer)*

- **Les états n'utilisent que `zinc`, `red`, `amber`, `green`, `blue`.
  `violet` sert à l'identité et à l'interaction** — fond ou barre,
  jamais en couleur de texte (sauf liens Markdown définis dans
  `index.css`). (ADR-026)
- **Les graphiques utilisent les teintes `data-1`, `data-2`, `data-3`
  (cyan, indigo, magenta), dans cet ordre.** Seulement dans
  `design/charts/`, jamais les familles CSS en brut. (ADR-047)
- **L'app Tauri n'expose ni `fs:*` ni `shell:*`** : le frontend passe par
  `routers/fs.py`. (ADR-040)
- **Rien n'est décoratif dans le Bureau.** Un sprite d'état rend une donnée du
  store de run ou de l'API ; sans donnée, rien (mobilier sans état permis). Tout sprite vient de `lib/bureau/sprites/` : `<use>` du `<defs>`
  commun, tons de `sprites-theme.css`, états `etat-*`. (ADR-070, ADR-058, ADR-026)
- **Un agent de produit ne se dessine que depuis `services[].activite`.**
  Lu borné et résolu dans le projet ; absent, périmé, hors schéma ou service
  arrêté : aucun agent. Tessera ne l'écrit pas et n'appelle aucune route du
  produit.
  (ADR-064, ADR-058)

## Documentation

*(doc-technique, doc-fonctionnelle)*

- **Une édition de documentation cite le code livré qui la fonde.** Un
  nombre, un numéro d'ADR ou un nom absent du diff et des fichiers fournis
  n'entre pas dans la doc ; le texte d'un ticket dit l'intention, pas les
  faits. (ADR-057)

## Langue

- **Identifiants, docstrings, noms de tests, messages de commit et titres
  de PR s'écrivent en anglais.** Commentaires, ADR, tickets et prompts
  restent en français. (ADR-044)

## Tests et stack

*(codeur)*

- **Tests frontend : Vitest + React Testing Library, pas Jest. Monaco est
  bundlé depuis `monaco-editor` via Vite, pas de CDN.** (ADR-014, ADR-012)
- **Pas de gestionnaire d'état global (Zustand, Jotai) tant que l'état
  partagé tient dans `useActiveProject` et `runStore.ts`** ; à revoir au-delà
  de 5 états globaux. (ADR-013)
