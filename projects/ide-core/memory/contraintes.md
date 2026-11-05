# Contraintes en vigueur

Règles que les agents doivent respecter aujourd'hui. Chaque règle renvoie à
son ADR source. La justification et l'histoire complète vivent dans
`decisions.md`.

---

## Proposées

Cette section n'est injectée dans aucun appel d'agent. Une règle nouvelle
s'écrit ici, avec son ADR ; un humain l'accepte en la déplaçant dans sa
section. (ADR-055)

- **Le superviseur n'agit que par les actions d'un registre fermé**, choisies
  dans une sortie validée par un schéma ; son modèle n'a ni outil ni `Bash`.
  Une sortie absente, hors schéma ou hors registre : aucune action.
  (ADR-080, ADR-061, ADR-039)
- **Le superviseur ne touche jamais** à l'argent (budgets, quotas, autonomie),
  à une suppression (fichier, branche, worktree, ticket annulé), à un secret, à
  un projet `confidentiality: professional`, ni à `agents.json`, `.github/`,
  `CLAUDE.md`, `.git/`. Une règle ou une leçon qui touche une porte (ADR-027,
  031, 037, 039, 053, 055, 067, 073) ou le superviseur lui-même ne se décide
  pas : elle va dans « À toi ». (ADR-080)
- **La délégation se déclare dans `pipeline.superviseur` de `agents.json`, par
  un humain.** Absente, le superviseur n'accepte ni n'écarte aucune règle ou
  leçon. Accepter n'est qu'un déplacement de bloc, que le code vérifie.
  (ADR-080, ADR-055, ADR-074)
- **Le superviseur ne merge jamais.** Il confie à `CIWatcher` une PR dont le
  run est approuvé, la tête encore `pushed_sha`, hors `resolveur-conflit`. Il
  ne relance une file qu'après une coupure d'infrastructure, une fois par cause,
  jamais sur « non approuvé ». (ADR-080, ADR-039, ADR-033, ADR-030)
- **Une écriture du superviseur est une intervention** : run `supervision` sous
  `RunLock`, une action par commit, une ligne dans `memory/supervision.md`.
  Tant qu'une file tient le projet, il n'écrit pas. Un diff de run qui touche
  ce journal met le run en `blocked`. (ADR-080, ADR-038, ADR-055)
- **`signaler` est l'unique chemin d'un agent vers le backlog d'ide-core.** Le
  projet source se déduit du run, jamais des arguments ; 3 signalements par
  run, 1 500 caractères ; secret ou terme interdit : refus ; projet
  `professional` : énumérations seules, sans texte libre. Aucun agent n'écrit
  dans le dépôt d'ide-core. (ADR-080, ADR-043, ADR-031, ADR-073)
- **Une revue de projet est un run `design` qui n'écrit que `tickets/**` et
  `memory/**`** : dix tickets, cinq signalements, 3 $ au plus. Tout autre
  fichier touché met le run en `blocked`. (ADR-080)
- **Un numéro rendu par `prochain_numero.py` est un numéro pris**, utilisé ou
  non : il se réserve à l'appel. (ADR-080)


## Git et périmètre d'écriture

- **Un projet qui déclare `worktree` exécute chaque run dans son worktree,
  jamais dans le checkout.** Sous `IDE_WORKTREES_DIR/<projet>/<ticket>`,
  créé depuis `origin/<base>` avec `core.longpaths` : c'est la racine
  d'écriture du run. Les sessions humaines n'y travaillent pas. (ADR-056)
- **Un lien de `populate` ne vise que ce que git ignore, et se retire avant
  toute suppression récursive.** Ce qui s'édite se copie. Jamais le `.env` de
  Tessera ; une entrée absente se journalise sans bloquer. (ADR-056, ADR-053)
- **Ne jamais écrire hors de la racine d'écriture du run** — le projet, son
  worktree (ADR-056) ou le dépôt ancêtre si `git_root: ancestor`. Un hook
  `PreToolUse` bloque ailleurs `Write`, `Edit`, `NotebookEdit` et les
  redirections Bash simples. Lire hors du projet reste permis, sauf le `.env`
  de Tessera. (ADR-031, ADR-053)
- **Le service de documentation n'écrit dans `agents.json` que la clé
  `description`**, proposée par doc-technique et contrôlée (preuve, 220
  caractères, une ligne). (ADR-068, ADR-027, ADR-057)
- **Ne jamais émettre une commande git ou `gh` en écriture.** Le hook
  `PreToolUse` n'admet que des lectures nommées (liste blanche, options globales
  lues avant ; `-c` cosmétique seulement). `agents.json`, `.git/`,
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
  service seul.** Seule `## En vigueur`, où un humain la déplace, atteint le
  codeur et le reviewer. Un diff de run qui touche ce fichier met le run en
  `blocked`. (ADR-074, ADR-055)
- **Avant toute création de branche, `git rev-parse --show-toplevel` doit
  renvoyer le dossier du projet**, sinon `NotAGitRepository` ; exception :
  `git_root: ancestor`. (ADR-024, ADR-028)

## Livraison et autonomie

- **Chaque run s'exécute sur sa propre branche et finit toujours par un
  commit.** Approuvé : type du ticket. Non approuvé :
  `chore: … — unapproved work (…)`. L'arbre ne reste jamais sale.
  (ADR-018)
- **Le chat commite sur une branche `chat-<horodatage>`, comme un run.**
  Il ne laisse jamais l'arbre sale. (ADR-019)
- **Ne jamais forcer un push.** Un push refusé est une information, pas un
  obstacle à contourner. (ADR-022)
- **Déclarer le niveau d'autonomie dans `agents.json`** (`autonomy:
  commit | pr | merge`, défaut : `commit`). Le merge n'intervient que sur
  CI verte — sauf `merge_without_ci: true`. (ADR-029, ADR-045)
- **Une approbation vaut pour un commit précis.** Avant le push, seuls des
  commits de rangement (`tickets/**`, `memory/pipeline-log.md`) peuvent suivre
  `approved_sha`, sinon `blocked` sans push. `CIWatcher` ne merge qu'une PR dont
  la tête relue est encore `pushed_sha`, merge lié à ce SHA ; sinon `blocked`,
  PR ouverte. (ticket-492, ADR-039)
- **Un run non approuvé ne se livre jamais.** Les exceptions de livraison
  restent dans `Livraison.arret` et ne font pas échouer le run. (ADR-030)
- **Sur un conflit de rebase, `resolveur-conflit` tente.** Une résolution
  qui aboutit ouvre sa PR et ne se merge jamais seule, même sur un projet
  en `merge`. Tout doute annule tout. (ADR-033)
- **La phase 1 de livraison (rebase, push, PR) libère le verrou du
  projet.** La phase 2 (attente CI, merge) tourne dans `CIWatcher`, en
  fond. `depends_on` bloque le ticket suivant jusqu'au merge. Une CI rouge
  met le ticket en `blocked`, PR laissée ouverte, sans relance. (ADR-051)
- **Une livraison attend, dans une limite de temps, que les PR déjà confiées
  à `CIWatcher` pour le projet soient mergées ou bloquées**, pour rebaser sur
  une base qui les porte. (ADR-065, ADR-051)
- **Une PR devenue conflictuelle ne se met à jour que par un merge de la base
  dans sa tête poussée, sans push forcé.** Sa tête doit encore être `pushed_sha` ;
  seuls des conflits de journaux résolus en union sont admis, sans agent.
  (ADR-069, ADR-022, ADR-039)

## Portes qui échouent fermées

- **Toute exception en production termine le run en `blocked` avec
  commit.** Jamais une erreur serveur, jamais un arbre sale. (ADR-037)
- **Un worktree qui porte du travail non commité ne se supprime pas.** Au
  démarrage, un worktree orphelin se commite comme un run non approuvé, puis
  se supprime. (ADR-056, ADR-037)
- **Le détecteur d'anomalies observe sans gouverner** : sans LLM, `git` ni
  `gh`, il n'arrête, ne relance ni ne modifie aucun run et n'écrit dans aucun
  dépôt ; son échec n'atteint jamais un run. (ADR-078, ADR-037)
- **Un projet ne porte qu'un run à la fois.** `RunLock` refuse le second
  et renvoie 409. Deux projets distincts tournent en parallèle. (ADR-038)
- **L'audit sécurité et le validateur échouent fermés.** Provider
  indisponible, réponse illisible ou exception →
  `BLOCK` / `CHANGES_REQUESTED`. Une faille `CRITICAL` ou `HIGH` bloque
  quel que soit le verdict LLM. (ADR-039)
- **En mode autonome, vérifier dépense estimée et quota réel entre deux
  tickets.** Un quota inconnu ne bloque jamais. Ne jamais interrompre au
  milieu d'un ticket. (ADR-020)
- **Une question sans réponse reprend, passé `dialogue_timeout_s`, sur une
  hypothèse énoncée** ; en mode autonome, le délai ne démarre pas. (ADR-025)

## Artefacts et projets

- **Les artefacts Tessera s'excluent via `.git/info/exclude`, jamais via
  `.gitignore`.** (ADR-021)
- **Les artefacts d'un projet cloné ou importé restent `local` par défaut,
  ceux d'un projet créé par l'IDE sont versionnés** ; un autre mode se déclare.
  (ADR-023)
- **Les services d'un projet se déclarent dans `agents.json`
  (`services: [{nom, commande}]`).** Rien de déclaré : pas de bouton de
  lancement. (ADR-042)
- **Un run ne lance ni serveur ni capture sans `pipeline.controle_visuel`
  déclaré.** L'app démarre depuis le worktree du run, sur un port libre, sans
  tuer de processus existant ; les captures restent hors du dépôt.
  (ADR-062, ADR-042, ADR-021)

*(codeur, reviewer)*

- **`ProjectLoader.list_projects()` ne liste que les dossiers avec un
  `CLAUDE.md`.** La fonction module-level reste disponible pour les tests
  et scripts. (ADR-006)
- **`Project.name` s'extrait du premier `# Titre` du `CLAUDE.md`**, avec
  fallback sur le nom du dossier. (ADR-007)

## Provider et orchestration

- **Les services passent toujours par `LLMProvider` (`complete`/`stream`),
  jamais par le SDK directement.** (ADR-017)
- **Chaque rôle déclare `provider`, `model` et `fallback` dans `agents.json`**
  (défaut `agent_sdk`), construits par `provider_pour_role`. Le repli ne part
  que sur indisponibilité (`provider_fallback`), run `rapide` ou prompt au-delà
  du `fallback_above_chars` d'un rôle `ollama`, jamais sur une réponse
  illisible. (ADR-046, ADR-059, ADR-071)
- **Un rôle déclaré `"web": true` reçoit `WebFetch` et `WebSearch` et
  perd `Bash`.** (ADR-049)

*(architect, codeur, reviewer)*

- **Un run démarre par `POST /orchestrator/run` et s'observe sur
  `WS /orchestrator/observe`.** `RunRegistry` tient les runs vivants et
  leur canal de dialogue. (ADR-041)
- **L'orchestrateur est instancié à chaque requête, sans état interne.**
  Ce qui survit entre requêtes (`RunLock`, `RunRegistry`) vit hors de
  lui. (ADR-008)
- **Le verdict du reviewer, de l'audit sécurité et du validateur se lit dans
  une sortie structurée validée par un schéma, jamais dans le texte.** Une
  sortie absente, hors schéma ou contradictoire refuse. (ADR-061, ADR-009)
- **Un module de `services/` vit dans son domaine et n'importe que son
  domaine ou un plus bas** (`ORDRE` de `test_domaines_services.py`). Aucun
  paquet de premier niveau hors `models`, `services`, `routers`, `utils`.
  (ADR-076)
- **Seuls les cinq réglages de `reglages.py` se changent depuis l'interface**,
  lus par `reglages.courants()` et figés à l'ouverture d'un run. Écrire exige
  un `Origin` déclaré ; aucun agent n'appelle `/api/v1/reglages`. (ADR-075,
  ADR-031)
- **`role: github-sync` est géré dans `POST /api/v1/agents/run`, pas
  dans un endpoint dédié.** (ADR-010)

## Confidentialité

- **Aucune donnée professionnelle dans un dépôt personnel** — nom de
  client, e-mail d'employeur, identifiant, jeton, hostname interne — ni
  dans le contenu ni dans les métadonnées git. (ADR-043)
- **Avant tout push, vérifier le diff ajouté, les messages de commit et
  les auteurs contre `FORBIDDEN_TERMS`.** Un projet déclare
  `"confidentiality": "professional"` pour s'exempter. (ADR-048)
- **Un secret de Tessera se lit : environnement, coffre du système, puis
  `.env`** (`SECRETS_SOURCE=auto` ; `coffre` exige le coffre, `env` pour la CI
  et Docker). Il n'est ni exporté à un sous-processus, ni affiché, ni passé en
  argument, et ne va à aucun agent ; seule une action de l'utilisateur crée une
  ressource en ligne. Aucun agent n'exécute le coffre (`keyring`, `cmdkey`,
  `coffre_cli`). (ADR-073, ADR-053)
- **Les termes interdits sont arrêtés à trois portes :** push pipeline,
  hook `pre-push`, CI sur chaque PR. Une porte qui ne peut pas juger
  refuse. (ADR-050)

## Interface et design

*(codeur, reviewer)*

- **Les états n'utilisent que `zinc`, `red`, `amber`, `green`, `blue`.
  `violet` sert à l'identité et à l'interaction** — fond ou barre,
  jamais en couleur de texte (sauf liens Markdown définis dans
  `index.css`). Un test verrouille ces règles. (ADR-026)
- **Les graphiques utilisent les teintes `data-1`, `data-2`, `data-3`
  (cyan, indigo, magenta), dans cet ordre fixe.** Seulement dans
  `design/charts/`, jamais les familles CSS en brut. (ADR-047)
- **L'app Tauri n'expose aucune permission `fs:*` ou `shell:*`.** Le
  frontend passe toujours par `routers/fs.py`. (ADR-040)
- **Rien n'est décoratif dans le Bureau.** Un sprite d'état rend une donnée du
  store de run ou de l'API ; sans donnée, rien (mobilier et cosmétique sans état
  permis). Tout sprite vient de `lib/bureau/sprites/` : `<use>` du `<defs>`
  commun, tons de `sprites-theme.css`, états `etat-*`. (ADR-070, ADR-058, ADR-026)
- **Un agent de produit ne se dessine que depuis `services[].activite`.**
  Le backend lit ce fichier, borné en taille et résolu dans le projet ;
  absent, périmé, hors schéma ou service arrêté : aucun agent. Tessera
  ne l'écrit jamais et n'interroge aucune route du produit.
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

- **Vitest + React Testing Library pour les tests frontend.** Pas de
  Jest. (ADR-014)
- **Monaco Editor est bundlé depuis `monaco-editor` via Vite.** Pas de
  CDN. (ADR-012)
- **Pas de gestionnaire d'état global (Zustand, Jotai) tant que l'état
  partagé tient dans `useActiveProject` et le store de run
  (`runStore.ts`, `useSyncExternalStore`).** À réévaluer au-delà de 5
  états globaux partagés. (ADR-013)
