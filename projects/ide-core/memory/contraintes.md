# Contraintes en vigueur

Règles que les agents doivent respecter aujourd'hui. Chaque règle renvoie à
son ADR source. La justification et l'histoire complète vivent dans
`decisions.md`.

---

## Proposées

Cette section n'est injectée dans aucun appel d'agent. Une règle nouvelle
s'écrit ici, avec son ADR ; un humain l'accepte en la déplaçant dans sa
section. (ADR-055)

- **Le service de documentation n'écrit dans `agents.json` que la clé
  `description`.** Aucun agent n'écrit ce fichier : doc-technique propose le
  texte, le service le contrôle (preuve, 220 caractères, une ligne) et le
  remplace sans toucher au reste du fichier. (ADR-068, ADR-027, ADR-057)

## Git et périmètre d'écriture

- **Un projet qui déclare `worktree` exécute chaque run dans son worktree,
  jamais dans le checkout.** Sous `IDE_WORKTREES_DIR/<projet>/<ticket>`,
  créé depuis `origin/<base>` avec `core.longpaths` : c'est la racine
  d'écriture du run. Les sessions humaines n'y travaillent pas. (ADR-056)
- **Un lien de `populate` ne vise que ce que git ignore, et se retire avant
  toute suppression récursive.** Ce qui s'édite se copie. Jamais le `.env` de
  Tessera ; une entrée absente se journalise sans bloquer. (ADR-056, ADR-053)

- **Ne jamais écrire hors de la racine d'écriture du run** — le projet, ou
  son worktree s'il en déclare un (ADR-056). Un hook `PreToolUse`
  bloque `Write`, `Edit`, `NotebookEdit` et les redirections Bash simples
  (`>`, `>>`, `tee`) vers tout chemin hors du dossier du projet — ou du
  dépôt ancêtre pour les projets qui déclarent `git_root: ancestor`.
  Lire hors du projet reste permis, sauf le `.env` de Tessera. (ADR-031,
  ADR-053)
- **Ne jamais émettre une commande git ou `gh` en écriture.** Le hook
  `PreToolUse` n'admet que des lectures nommées : une sous-commande absente
  de la liste blanche est refusée, options globales lues avant elle ; `-c`
  n'accepte que des clés cosmétiques. `agents.json`, `.git/`,
  `.claude/settings*.json` et `.github/workflows/` se refusent aussi en
  écriture. (ADR-067, ADR-027)
- **Le script que `test_command` lance se refuse en écriture**, comme
  `agents.json` : le premier argument qui désigne un fichier existant, résolu
  depuis `pipeline.test_cwd`. Un diff qui touche la configuration des tests
  (`conftest.py`, `[tool.pytest*]`, `[tool.mypy]`, `vitest.config.*`,
  `eslint.config.*`, `tsconfig*.json`, `scripts` de `package.json`) s'ouvre,
  pour le reviewer, sur un avertissement qui les nomme. (ADR-027)
- **Une règle nouvelle s'écrit sous `## Proposées` dans `contraintes.md`,
  avec son ADR.** Un diff qui modifie ce fichier ailleurs met le run en
  `blocked` : un humain accepte la règle en la déplaçant dans sa section.
  (ADR-055)
- **Avant toute création de branche, vérifier que `git rev-parse
  --show-toplevel` renvoie exactement le dossier du projet.** Sinon,
  lever `NotAGitRepository`. Exception déclarée : `git_root: ancestor`
  dans `agents.json`. (ADR-024, ADR-028)

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
- **Une approbation vaut pour un commit précis.** `approved_sha` se note à
  l'approbation ; avant le push, seuls des commits de rangement du pipeline
  (`tickets/**`, `memory/pipeline-log.md`) peuvent le suivre, sinon le run est
  `blocked` sans push. `CIWatcher` ne merge pas une PR dont la tête n'est plus
  `pushed_sha` : ticket `blocked`, PR ouverte. La tête se relit après le
  verdict de la CI, et le merge est lié à `pushed_sha` (champ `sha` de l'API
  GitHub). Un SHA inconnu refuse aussi.
  (ticket-492, ADR-039)
- **Un run non approuvé ne se livre jamais.** Les exceptions de livraison
  restent dans `Livraison.arret` et ne font pas échouer le run. (ADR-030)
- **Sur un conflit de rebase, `resolveur-conflit` tente.** Une résolution
  qui aboutit ouvre sa PR et ne se merge jamais seule, même sur un projet
  en `merge`. Tout doute annule tout. (ADR-033)
- **La phase 1 de livraison (rebase, push, PR) libère le verrou du
  projet.** La phase 2 (attente CI, merge) tourne dans `CIWatcher`, en
  fond. `depends_on` bloque le ticket suivant jusqu'au merge. Une CI rouge
  met le ticket en `blocked`, PR laissée ouverte, sans relance. (ADR-051)
- **La livraison d'un ticket attend que les PR déjà confiées à `CIWatcher`
  pour le projet soient mergées ou bloquées, dans une limite de temps.**
  Le rebase se fait ainsi sur une base qui les porte ; passé le délai, la
  livraison part comme avant. (ADR-065, ADR-051)

## Portes qui échouent fermées

- **Toute exception en production termine le run en `blocked` avec
  commit.** Jamais une erreur serveur, jamais un arbre sale. (ADR-037)
- **Un worktree qui porte du travail non commité ne se supprime pas.** Au
  démarrage, un worktree orphelin se commite comme un run non approuvé, puis
  se supprime. (ADR-056, ADR-037)
- **Un projet ne porte qu'un run à la fois.** `RunLock` refuse le second
  et renvoie 409. Deux projets distincts tournent en parallèle. (ADR-038)
- **L'audit sécurité et le validateur échouent fermés.** Provider
  indisponible, réponse illisible ou exception →
  `BLOCK` / `CHANGES_REQUESTED`. Une faille `CRITICAL` ou `HIGH` bloque
  quel que soit le verdict LLM. (ADR-039)
- **En mode autonome, vérifier dépense estimée et quota réel entre deux
  tickets.** Un quota inconnu ne bloque jamais. Ne jamais interrompre au
  milieu d'un ticket. (ADR-020)
- **Une question sans réponse reprend sur une hypothèse énoncée.** Passé
  `dialogue_timeout_s`, l'agent choisit et énonce son hypothèse. En mode
  autonome, le délai ne démarre pas. (ADR-025)

## Artefacts et projets

- **Les artefacts Tessera s'excluent via `.git/info/exclude`, jamais via
  `.gitignore`.** (ADR-021)
- **Les artefacts d'un projet cloné ou importé restent `local` par
  défaut ; ceux d'un projet créé par l'IDE sont versionnés.** Le mode suit
  la façon dont le projet est arrivé ; un autre se déclare explicitement.
  (ADR-023)
- **Les services d'un projet se déclarent dans `agents.json`
  (`services: [{nom, commande}]`).** Rien de déclaré : pas de bouton de
  lancement. (ADR-042)
- **Un run ne lance ni serveur ni capture sans `pipeline.controle_visuel`
  déclaré.** Fichiers d'interface, largeurs et démarrage se déclarent, jamais
  devinés ; l'app démarre depuis le worktree du run, sur un port libre, et
  ne tue jamais un processus existant. Les captures restent hors du dépôt.
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
- **Déclarer `provider`, `model` et `fallback` dans `agents.json` pour
  chaque rôle ; un rôle sans `provider` prend `agent_sdk`.** Toute
  construction de provider passe par `provider_pour_role`. Seuls une
  indisponibilité, qui émet `provider_fallback`, ou un run lancé `rapide`
  déclenchent le repli. Une réponse illisible n'en déclenche aucun.
  (ADR-046, ADR-059)
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
- **`role: github-sync` est géré dans `POST /api/v1/agents/run`, pas
  dans un endpoint dédié.** (ADR-010)

## Confidentialité

- **Aucune donnée professionnelle dans un dépôt personnel** — nom de
  client, e-mail d'employeur, identifiant, jeton, hostname interne — ni
  dans le contenu ni dans les métadonnées git. (ADR-043)
- **Avant tout push, vérifier le diff ajouté, les messages de commit et
  les auteurs contre `FORBIDDEN_TERMS`.** Un projet déclare
  `"confidentiality": "professional"` pour s'exempter. (ADR-048)
- **Un jeton de service en ligne (Vercel, Stripe, Resend, Cloudflare) ne
  quitte pas le `.env` de Tessera.** Un agent ne le reçoit pas, ne lit pas ce
  fichier et ne crée aucune ressource en ligne : seule une action de
  l'utilisateur le fait. (ADR-053)
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
- **Rien n'est décoratif dans le Bureau.** Chaque sprite, objet ou bulle rend
  un état que le store de run ou l'API fournit ; sans donnée, on ne le
  dessine pas. Seul le mobilier d'une salle se dessine toujours : il ne s'anime
  pas et ne porte aucun voyant. Les sprites vivent sous `design/bureau/`, leurs
  tons sont des jetons `--sprite-*` du `@theme`, jamais une famille CSS brute.
  (ADR-058)
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
