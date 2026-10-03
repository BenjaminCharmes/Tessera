# Contraintes en vigueur

Règles que les agents doivent respecter aujourd'hui. Chaque règle renvoie à
son ADR source. La justification et l'histoire complète vivent dans
`decisions.md`.

---

## Git et périmètre d'écriture

- **Ne jamais écrire hors de la racine du projet.** Un hook `PreToolUse`
  bloque `Write`, `Edit`, `NotebookEdit` et les redirections Bash simples
  (`>`, `>>`, `tee`) vers tout chemin hors du dossier du projet — ou du
  dépôt ancêtre pour les projets qui déclarent `git_root: ancestor`.
  Lire hors du projet reste permis. (ADR-031)
- **Ne jamais émettre une commande git ou `gh` en écriture.** Le hook
  `PreToolUse` refuse toute tournure — chemin, casse, enveloppe, alias.
  Le git en lecture reste permis. `agents.json`, `.git/`,
  `.claude/settings*.json` et `.github/workflows/` se refusent aussi en
  écriture. (ADR-027)
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
- **Un run non approuvé ne se livre jamais.** Les exceptions de livraison
  restent dans `Livraison.arret` et ne font pas échouer le run. (ADR-030)
- **Sur un conflit de rebase, `resolveur-conflit` tente.** Une résolution
  qui aboutit ouvre sa PR et ne se merge jamais seule, même sur un projet
  en `merge`. Tout doute annule tout. (ADR-033)
- **La phase 1 de livraison (rebase, push, PR) libère le verrou du
  projet.** La phase 2 (attente CI, merge) tourne dans `CIWatcher`, en
  fond. `depends_on` bloque le ticket suivant jusqu'au merge. Une CI rouge
  met le ticket en `blocked`, PR laissée ouverte, sans relance. (ADR-051)

## Portes qui échouent fermées

- **Toute exception en production termine le run en `blocked` avec
  commit.** Jamais une erreur serveur, jamais un arbre sale. (ADR-037)
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
- **`local` est le défaut quand `agents.json` est absent ou illisible.**
  Le mode `tracked` se déclare explicitement. (ADR-023)
- **Les services d'un projet se déclarent dans `agents.json`
  (`services: [{nom, commande}]`).** Rien de déclaré : pas de bouton de
  lancement. (ADR-042)

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
  chaque rôle.** Toute construction de provider passe par
  `provider_pour_role`. Seule une indisponibilité déclenche le repli, qui
  émet `provider_fallback`. Une réponse illisible n'en déclenche aucun.
  (ADR-046)
- **Un rôle déclaré `"web": true` reçoit `WebFetch` et `WebSearch` et
  perd `Bash`.** (ADR-049)

*(architect, codeur, reviewer)*

- **Un run démarre par `POST /orchestrator/run` et s'observe sur
  `WS /orchestrator/observe`.** `RunRegistry` tient les runs vivants et
  leur canal de dialogue. (ADR-041)
- **L'orchestrateur est instancié à chaque requête, sans état interne.**
  Ce qui survit entre requêtes (`RunLock`, `RunRegistry`) vit hors de
  lui. (ADR-008)
- **Le verdict reviewer se parse par mot-clé :** la première ligne qui
  commence par `APPROVED` ou `CHANGES_REQUESTED` l'emporte. Sans ligne de
  verdict, `CHANGES_REQUESTED` n'importe où prime, et une réponse sans
  verdict refuse. (ADR-009)
- **`role: github-sync` est géré dans `POST /api/v1/agents/run`, pas
  dans un endpoint dédié.** (ADR-010)

## Confidentialité

- **Aucune donnée professionnelle dans un dépôt personnel** — nom de
  client, e-mail d'employeur, identifiant, jeton, hostname interne — ni
  dans le contenu ni dans les métadonnées git. (ADR-043)
- **Avant tout push, vérifier le diff ajouté, les messages de commit et
  les auteurs contre `FORBIDDEN_TERMS`.** Un projet déclare
  `"confidentiality": "professional"` pour s'exempter. (ADR-048)
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
  partagé tient dans `useActiveProject`.** À réévaluer au-delà de 5
  états globaux partagés. (ADR-013)
