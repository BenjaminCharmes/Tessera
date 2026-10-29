# Audit de sécurité — API, gardes des agents, frontend

État au 2026-10-29. Complète `docs/audit/regles.md` (tests des règles) et
`docs/audit/adr.md` (statuts des ADR). L'agent `securite` audite le diff d'un run ;
ici, c'est le code déjà en place.

## Méthode et limites

Lecture seule, par recherche et lecture de fichiers. **Aucun test lancé, aucun script
exécuté, aucun exploit rejoué.** Un scénario décrit ce qu'une forme de commande ou de
requête ferait d'après le code lu ; il n'a pas été vérifié en exécution. Les formes
nommées sont des entrées de test à écrire, pas des instructions.

Gravités, comme l'audit des runs :

- **CRITICAL** : effet distant ou exécution de code, sans autre précondition que l'état
  par défaut ou une forme naturelle de commande.
- **HIGH** : un garde d'ADR-027, ADR-031 ou ADR-053 est contourné, ou un secret sort.
- **MEDIUM** : contournement qui exige une intention, ou une précondition réaliste.
- **LOW** : durcissement, fuite d'information mineure.

Preuve d'un test : **gardée**, **partielle** ou **aucun test**, comme dans `regles.md`.
Les corps de test ne sont relus que pour les gardes de §3.

**Non lu** (à dire plutôt qu'à omettre) : sur environ 280 fichiers backend, ne sont lus
que les gardes, `auth.py`, `main.py`, `config.py`, `env_sdk.py`, `agent_sdk.py` (options
et hooks), les routeurs `fs`, `captures`, `services*`, `signalements` et une partie de
`projects`, `git_clone`, `git_link`, `project_importer`, `process_registry` (découpage
de la commande). Restent hors lecture : `routers/orchestrator.py`, `observation.py`,
`chat.py`, `runs.py`, `agent_admin.py`, `ticket_proposals.py`, `services/project_removal.py`,
`provisioning`, `ci_watcher`, `github_sync`, la construction du frontmatter YAML d'un
ticket signalé, le script du hook `pre-push`, et côté frontend `lib/ws.ts`.

## Ce que l'audit établit en une page

- **2 constats CRITICAL** : un `git push` préfixé d'une assignation de variable passe le
  garde git (S-01), et l'API ouverte par défaut n'est protégée ni contre un `Host`
  étranger ni contre un `Origin` étranger, alors qu'elle peut fixer une `test_command`
  puis lancer un run (S-02).
- **7 HIGH** : le garde git/gh est une liste noire, et la liste noire a des trous
  nombreux (S-03 à S-06) ; le `.env` de Tessera et les manifestes des projets voisins
  s'écrivent depuis le projet bootstrap (S-07, S-08) ; `fs.py` n'applique aucune
  protection de chemin à l'écriture (S-09).
- **Le plafond est déjà dit** par ADR-027 (« pas une évasion ») et ADR-031. Ce qui ne
  l'est pas : la règle de `contraintes.md` promet « toute tournure — chemin, casse,
  enveloppe, alias », ce que le code ne tient pas pour des formes aussi simples qu'une
  assignation ou un mot-clé de shell. L'écart est entre la règle écrite et le garde,
  pas entre le garde et l'évasion délibérée.
- **Ce qui tient** (§4) : confinement de `fs.py` par résolution de liens, identifiants de
  projet validés en entier, services lancés sans shell, arrêt par pid sur liste blanche,
  captures servies par motif, URL de clone et de remote bornées, DOMPurify, jetons
  neutralisés dans l'environnement du CLI.
- **Frontend** : aucun constat au-dessus de LOW.

## 1. Constats

Un constat par entrée : gravité, `fichier:ligne`, scénario. « Précondition » dit ce qu'il
faut en plus.

### CRITICAL

**S-01 — Une assignation de variable en tête d'un segment rend le git invisible.**
`services/providers/git_guard.py:85-101`. `_segment_interdit` lit le premier jeton du
segment. `nom_de_commande("<VAR>=<valeur>")` rend `<var>=<valeur>`, qui n'est ni un
shell, ni `eval`, ni une enveloppe, ni `git`, ni `gh` : la fonction rend `False` (l.101)
sans regarder la suite. `ENVELOPPES` ne couvre que `env <VAR>=…`, pas l'assignation nue
(`test_git_guard.py:177` teste `env FOO=bar git push`, pas `FOO=bar git push`).
Scénario : un agent écrit `GIT_AUTHOR_NAME=x git commit …` — une forme naturelle, sans
intention de contourner — et le commit passe ; avec `push --force`, c'est la
violation d'ADR-022 que le garde existe pour empêcher.
Précondition : aucune. Preuve : **aucun test** de la forme.

**S-02 — L'API ouverte par défaut ne contrôle ni `Host` ni `Origin`.**
`main.py:125-136`, `auth.py:70-82`. Vide, `STATIC_TOKEN` laisse tout passer ; le CORS
(`allow_origins=["http://localhost:5173"]`) n'empêche que la *lecture* d'une réponse par
une page tierce, et ne s'applique pas aux WebSocket. Aucun `TrustedHostMiddleware`,
aucune vérification d'`Origin` sur le handshake.
Scénario : une page web visitée par l'utilisateur ouvre une WebSocket vers
`/orchestrator/observe` (lecture du contenu des runs), ou, par rebond DNS (le navigateur
croit rester sur le même site, `Host` étranger accepté), appelle `PATCH
/projects/{id}/pipeline` (`projects.py:663`) pour fixer `test_command`, `autonomy:
merge` et `merge_without_ci`, puis `POST /orchestrator/run`. La commande de test
s'exécute alors sous l'identité de l'utilisateur.
Précondition : l'utilisateur visite la page pendant que le backend tourne ; non rejoué.
À vérifier : si FastAPI accepte un corps JSON sous `text/plain` (formulaire sans
preflight), le rebond n'est même pas nécessaire. `docs/configuration.md:50` et
`CLAUDE.md` disent « interface de confiance » : `127.0.0.1` n'est pas une frontière
contre le navigateur de l'utilisateur. Preuve : `test_auth_static_token.py` garde le
token ; **aucun test** de `Host` ni d'`Origin`.

### HIGH

**S-03 — `gh` : une option avant la sous-commande masque `pr merge`.**
`git_guard.py:98-100`. La sous-commande est le premier jeton qui ne commence pas par
`-`. Pour `gh --repo <o/r> pr merge`, ce jeton est la valeur de l'option, qui n'est pas
dans `_SOUS_COMMANDES_GH_INTERDITES` (l.53) : le segment passe. Scénario : fusionner une
PR sur un dépôt nommé, sans le garde. Précondition : une session `gh` authentifiée sur la
machine. Preuve : **aucun test** de la forme.

**S-04 — `gh` hors liste : `auth token`, `alias set`, `secret`, `issue`, `gist`, `run`.**
`git_guard.py:53`. Seuls `pr`, `api`, `repo`, `release`, `workflow` sont refusés. `gh auth
token` imprime le jeton de l'utilisateur dans la sortie que l'agent lit (donc dans le
transcript) — ADR-053 dit qu'aucun agent ne reçoit un jeton. `gh alias set` définit un nom
qui recouvre `pr merge`, puis le nom seul passe. `gh secret`, `gh run rerun`, `gh issue`
écrivent sur GitHub. Le test `test_git_guard.py:196` impose que `gh auth status` passe :
c'est la lecture qu'on veut garder, et la liste noire ne sait pas la séparer de
`auth token`. Preuve : **aucun test** des formes interdites.

**S-05 — Git « en lecture » qui exécute une commande, ou qui livre un secret.**
`git_guard.py:29-34, 68-72`. `-c <clé>=<valeur>` n'est inspecté que pour `alias.`. Une
clé comme `core.fsmonitor`, `core.pager` ou `diff.external` fait lancer une commande par
un `git status`, `git log` ou `git diff` ; `git bisect run <commande>` et `git difftool
-x` aussi : aucune de ces sous-commandes n'est dans la liste. `git credential fill`, qui
rend le mot de passe ou le jeton que le gestionnaire d'identifiants garde, n'y est pas
non plus. Scénario : l'agent exécute un push ou lit un jeton sous couvert d'un git
de lecture. Preuve : **aucun test**.

**S-06 — Mots-clés de shell et shells non listés.**
`git_guard_lexique.py:23, 20`, `git_guard.py:101`. `SHELLS` ne contient ni `cmd`, ni
`powershell`, ni `pwsh` ; ce dépôt tourne sous Windows. Les mots-clés qui introduisent
une commande — `{`, `then`, `do`, `else`, `!` — sont pris pour le nom de la commande, et
le segment passe : `if true; then git push; fi` est découpé en `if true`, `then git push`,
`fi`. Preuve : `test_git_guard.py:151-178` liste 24 tournures, aucune de celles-ci.

**S-07 — Le `.env` de Tessera s'écrit depuis le projet bootstrap.**
`chemins_proteges.py:68-105`, `garde_jetons.py:105-117`, `agents.json` d'ide-core
(`git_root: ancestor`, aucune clé `worktree`). Le garde-jetons ne refuse que des
*lectures*. `motif_de_protection` ne nomme pas `.env`. Sous `ancestor`, la racine
d'écriture est le dépôt entier : une redirection Bash ou un `Write` vers `.env` à la
racine du dépôt est dans le périmètre. Scénario : vider `FORBIDDEN_TERMS` (la porte
d'ADR-050) ou changer `STATIC_TOKEN` depuis un run. Précondition : un run ide-core.
(`Write` sur un fichier existant exige aussi une lecture préalable, que le garde refuse :
reste la redirection Bash et la création.) Preuve : **aucun test**.

**S-08 — Les manifestes des projets voisins s'écrivent sous `ancestor`.**
`chemins_proteges.py:68`. Seul `project_path/agents.json` est protégé. Sous `ancestor`, la
racine inclut `projects/<autre>/agents.json`, `scripts/hooks/pre-push` (la porte
d'ADR-050 en local) et `Makefile`. Scénario : un run ide-core passe un autre projet en
`autonomy: merge`, ou en `confidentiality: professional`, ce qui l'exempte des termes
interdits (ADR-048). Preuve : `test_chemins_proteges.py:143` fait passer
`tests/fixtures/agents.json` à dessein ; le cas d'un `agents.json` *voisin* n'est pas
testé.

**S-09 — `fs.py` n'applique aucune protection à l'écriture, et une cible de lien est une racine.**
`routers/fs.py:43-60, 121-131`, `project_importer.py:68-96`. `PUT /fs/write` confine par
résolution de liens, mais pas par `motif_de_protection` : `.git/hooks/*`, `agents.json`,
`.claude/settings*.json`, `.github/workflows/` s'écrivent par l'API. Un projet importé en
`symlink` ajoute sa cible résolue aux racines (`_workspace_roots`), et `_validate_source`
ne vérifie que l'existence : importer un dossier large en fait une racine lisible et
inscriptible par l'éditeur. Scénario : sous `STATIC_TOKEN` vide ou par S-02, importer
puis écrire un hook de dépôt, exécuté au prochain commit. Avec un token, c'est une action
de l'utilisateur et le constat tombe à MEDIUM. Preuve : `test_fs_router.py:174` garde le
lien posé *dans* le workspace ; **aucun test** de chemins protégés ni de source large.

### MEDIUM

**S-10 — `node -c` ne protège rien.** `redirections_bash.py:92`. Le filet de
ticket-326 cherche `-c` ; `node` lit son code derrière `-e`. Les motifs d'écriture
(`open(…,'w')`, `.write(`) sont ceux de Python : `writeFileSync` n'en fait pas partie. Côté
Python, `open(f, mode='w')` (mode nommé) et `shutil.copy` ne sont pas vus. Preuve :
`test_python_c_protection.py:59` garde `node -c` *sans* écriture ; aucun test pour `-e`.

**S-11 — Formes de redirection non lues.** `redirections_bash.py:42-47`. Un jeton collé
(`echo x>../f`), `2>../f`, le second fichier de `tee a ../b`, et un chemin Windows à
antislash (`shlex` en mode POSIX le mange) ne sont pas rendus comme cibles. `cp`, `mv`,
`rm`, `sed -i`, `dd of=` ne sont pas lus du tout : `rm -r ../autre-projet` n'est pas une
écriture pour le garde. ADR-031 limite sa promesse à `>`, `>>`, `tee`, mais `echo x>../f`
est une redirection simple. Preuve : `test_perimetre_ecriture.py:199-222` ne couvre que
les formes à jetons séparés.

**S-12 — Un `git` « de lecture » qui écrit un fichier.** `git_guard.py:29-34`.
`--output=<chemin>` (`git diff`, `git log`) écrit où l'on veut, hors du contrôle
d'écriture qui ne regarde que `>`. Les commandes de plomberie — `commit-tree`,
`symbolic-ref`, `update-index`, `reflog expire`, `gc`, `hash-object -w`, `notes`,
`replace`, `init`, `clone`, `bundle` — ne sont pas dans la liste. `symbolic-ref HEAD` suffit
à déplacer la branche que le pipeline commitera. Preuve : **aucun test**.

**S-13 — Garde-jetons : glob, concaténation, dossier entier.** `garde_jetons.py:94-117`.
En Bash, seul un jeton dont le dernier segment est exactement `.env` est lu : `.e*`, `.en?`
et une concaténation passent, comme `grep -r <motif> ../..`. `Grep` avec `path` sur un dossier
et sans `glob` rend `False` (l.112-117). Le message de refus le dit déjà (« attrape une
erreur, pas une évasion »). Preuve : `test_garde_jetons.py` couvre les formes nommées ; les
contournements ne sont pas testés. À confirmer : si `Grep` descend dans les fichiers
cachés.

**S-14 — Les captures envoient le jeton de session à l'URL du manifeste.**
`captures_config.py:111`, `captures.py:95-124`. `url` accepte tout `http(s)://`. Le jeton lu
dans le `.env` du projet est transmis à l'exécuteur avec cette URL. Un `agents.json` importé
ou cloné qui déclare une adresse étrangère reçoit le jeton. Précondition : projet non sûr,
captures lancées. Preuve : **aucun test** de l'hôte.

**S-15 — Un manifeste de projet est du code.** `process_registry.py:131-175`,
`routers/services.py:97-143`, `PATCH /pipeline`. `services[].commande` et
`pipeline.test_command` viennent de `agents.json` ; le lancement n'utilise pas de shell et
`cwd` est borné au projet (bien), mais la commande elle-même est libre. Un projet cloné ou
importé d'un tiers l'exécute au clic. C'est voulu ; ce qui manque est un avertissement à
l'import et au clone. Décision de produit, pas de correction : voir §5.

**S-16 — Casse des noms protégés sous NTFS.** `chemins_proteges.py:77`. `cible.name in
_CONSIGNES` et la comparaison `.claude/skills` sont sensibles à la casse. `resolve()`
normalise un fichier **existant** ; un `claude.local.md` à créer garde sa casse, et le CLI,
sur un système insensible, le lit sous `CLAUDE.local.md`. À confirmer en exécution.

**S-17 — Les hooks du dépôt ne sont pas désarmés partout.** ADR-027 : « l'orchestrateur
n'exécute jamais les hooks du dépôt ». `core.hooksPath` n'apparaît que dans `socle.py`,
`reprise_orphelin.py` et `temporary_worktree.py`, sur 18 fichiers qui lancent git, dont
`git_link.py:148` (un `commit`). Ticket-677 (todo) le porte ; l'écart entre l'ADR et le
code est réel jusque-là.

**S-18 — Un signalement peut être posé par n'importe qui qui atteint l'API.**
`routers/signalements.py:70-90`. `POST /signalements` crée un ticket dans le backlog
d'ide-core ; une file autonome l'implémentera, en `autonomy: merge`. Aucune borne de taille
sur `description` et `contexte`. C'est une porte d'injection d'instructions vers un agent :
la même précondition que S-02, et la même correction. Le ticket naît avec une ligne de
critères qui le fait refuser par le validateur (`LIGNE_CRITERES`) : bonne défense, à garder.

### LOW

**S-19 — Le token WebSocket passe en query string, et le bundle l'embarque.**
`auth.py:43-45`, `lib/auth.ts:12-29`. `VITE_STATIC_TOKEN` est inliné dans le bundle
(`docs/configuration.md:82` le dit) ; la query peut finir dans le journal d'accès d'uvicorn.
Aucune porte contre : c'est le seul canal d'un navigateur. Retirer `token=` du journal.

**S-20 — Détails d'exception renvoyés.** `main.py:120` ne renvoie `str(exc)` que pour
`MissingPromptError` (message voulu, ticket-051) ; `services.py:139` renvoie `{exc}` d'un
`OSError`, qui nomme un chemin local. Par ailleurs, `git_clone._GITHUB_URL_RE` (l.20) et
`git_link._REPO_URL` (l.27) se terminent par `$` : en Python, un saut de ligne final passe
(à confirmer sur les deux motifs, non rejoué). Sans effet connu : l'URL est l'argument d'un
processus lancé sans shell.

**S-21 — Paramètre mort qui enverrait un jeton dans `.git/config`.** `git_clone.py:33-37`
insère `github_token` dans l'URL de clone ; `routers/projects.py:222` ne le passe pas.
Tant qu'il ne l'est pas, rien ne fuit. Le jour où il l'est, l'URL part dans la configuration
du remote.

**S-22 — `rel="noreferrer"` seul.** `LigneApp.tsx:31`, `AdresseDuService.tsx:20`. `noreferrer`
implique `noopener` dans les navigateurs actuels ; les trois autres liens et les deux
`window.open` portent `noopener`. Les `href` viennent de `lienDuDepot` (schéma borné à `http`,
`https`, ssh) ou de `localhost:<port>`. Aucun `dangerouslySetInnerHTML` hors
`MarkdownView.tsx:50`, qui passe par `DOMPurify.sanitize`. Aucun jeton dans `localStorage`.

## 2. Ce que l'audit ne tranche pas

- **Quels dossiers un utilisateur peut importer** (S-09) : une liste d'interdits (`~/.ssh`,
  le dossier personnel entier) ou une confirmation explicite. Décision de produit.
- **Avertir à l'import et au clone qu'un manifeste lance des commandes** (S-15) : idem.
- **Garder ou non la porte de la file autonome sur `autonomy: merge`** : hors périmètre.

## 3. Gardes d'ADR-027 et d'ADR-031 : les contournements connus sont-ils testés ?

Les noms de test viennent de `backend/tests/`. « Contournements connus » = ceux de §1.

| Garde | Tests lus | Contournements connus | Preuve |
|---|---|---|---|
| Git et `gh` en écriture (ADR-027) | `test_git_guard.py` : 24 tournures de ticket-119 refusées (`::test_les_tournures_triviales_sont_refusees`), 9 lectures permises (`::test_le_durcissement_ne_refuse_pas_la_lecture`), `::test_le_hook_est_installe_sur_chaque_appel_d_agent` | S-01, S-03, S-04, S-05, S-06, S-12 : aucune de ces formes dans les listes de paramètres | **partielle** : les formes de ticket-119 sont gardées, les contournements ci-contre n'ont **aucun test** |
| Fichiers de politique protégés (ADR-027) | `test_chemins_proteges.py::test_le_hook_refuse_les_chemins_qui_portent_la_politique`, `::test_le_depot_parent_d_un_projet_ancestor_est_protege_aussi`, `::test_les_fichiers_de_consignes_sont_proteges`, `::test_les_voisins_legitimes_passent` ; `test_perimetre_ecriture.py::test_le_hook_refuse_une_ecriture_a_travers_un_lien` | S-07, S-08, S-16 | **partielle** : le cœur est gardé ; `.env`, manifestes voisins et casse NTFS : **aucun test** |
| `python -c` / `node -c` (ADR-031, ticket-326) | `test_python_c_protection.py` : 11 tests, dont `::test_le_hook_refuse_python_c_write_claude_md` | S-10 : `node -e`, mode nommé, `shutil` | **partielle** : Python gardé pour ses formes nommées ; Node : **aucun test** d'écriture |
| Écriture hors racine (ADR-031) | `test_perimetre_ecriture.py` : voisin refusé, dépôt de Tessera, dossier personnel, préfixe commun (`client-attaque`), lien, redirection Bash, worktree | S-11 | **gardée** pour `>`, `>>`, `tee` à jetons séparés ; **aucun test** des formes collées, de `cp`/`mv`/`rm` |
| Hooks du dépôt jamais exécutés (ADR-027) | `test_hook_pre_push.py:285` : `GitWorkspaceService._run` envoie `core.hooksPath` | S-17 : 3 fichiers sur 18 | **partielle** ; ticket-677 (todo) |
| Politique lue une fois (ADR-027, ticket-119) | `test_politique_run.py::test_le_workspace_git_tient_la_racine_figee`, `::test_le_hook_de_perimetre_tient_la_racine_figee`, `::test_les_options_du_sdk_recoivent_la_racine_figee` | aucun connu | **gardée** (noms ; corps non relus) |
| Un commit qui échoue n'approuve pas (ADR-027) | `test_commit_integrite.py::test_un_commit_qui_echoue_empeche_l_approbation`, `::test_un_commit_qui_echoue_n_avance_pas_la_ref_de_base` | aucun connu | **gardée** |
| Garde-jetons (ADR-053) | `test_garde_jetons.py` : Read, Glob, Grep, Bash (8 formes), orthographe Git Bash, `::test_the_refusal_says_what_the_guard_cannot_do` | S-13 | **gardée** pour ce que le garde promet (un chemin nommé) ; contournements : **aucun test** |
| Jeton statique, HTTP et WebSocket (ticket-120) | `test_auth_static_token.py` : 14 tests, dont préflight, `/health`, mauvais jeton | S-02 | **gardée** pour le jeton ; **aucun test** de `Host` ni d'`Origin` |
| Confinement de `fs.py` (ticket-058) | `test_fs_router.py` : traversée, hors workspace, lien dans le workspace, lecture, écriture, liste | S-09 | **gardée** pour la sortie du workspace ; **aucun test** de chemin protégé ni de source d'import |

Le test `test_git_guard.py:196-197` (`gh auth status` passe) et
`test_garde_jetons.py` (`cat .env` du projet passe) fixent des **faux refus à éviter**. Un
correctif de S-04 ou de S-13 ne doit pas les casser.

## 4. Ce qui tient

Lu et jugé correct : `fs.py` résout les liens avant de comparer (`_resolve_inside_workspace`,
l.63-88) ; `project_id` est validé en entier (`fullmatch`, `utils/project_id.py:19`) et
appliqué en dépendance de route et en validateur de modèle, ce qui ferme `../` pour le clone
et l'import ; les services sont lancés par `create_subprocess_exec`, sans shell, `cwd` borné
au projet (`process_registry.py:171-175`) ; l'arrêt par pid passe par l'inventaire courant
(`services_running.py:50-56`) ; les captures se servent par motif de fichier et de ticket
(`captures.py:93-96`) ; l'URL de clone est bornée à `https://github.com/` (`git_clone.py:20`)
et celle du remote exclut `ext::` et tout préfixe `-` (`git_link.py:27-31`) ; le middleware
d'authentification est ASGI et couvre les WebSocket, la comparaison est à temps constant
(`auth.py:56`) ; `tools` est une liste explicite sans `WebFetch` ni `MultiEdit`
(`agent_sdk.py:80, 206`) ; les jetons de service sont vidés dans l'environnement du CLI
(`env_sdk.py:20-21`) ; la racine d'écriture est figée à la fabrication du hook
(`perimetre.py:141-146`).

## 5. Tickets de correction

**À écrire à la main ou par une file : ce ticket ne les crée pas** (il ne corrige rien).
Numérotation : le plus grand numéro vu est 684 ; chaque fiche prend son numéro de
`scripts/prochain_numero.py ticket` à la création. Un critère = un test nommé. Ordre :
`CRITICAL`, puis `HIGH`, puis `MEDIUM`, puis `LOW`.

### CRITICAL

**C-01 — Le garde git lit le premier mot réel d'un segment** (S-01, S-06) — `fix`,
indépendant des autres ; à faire avant C-03, qui réécrit le même fichier.
`git_guard_lexique.py`, `git_guard.py`.
- `test_leading_assignment_is_skipped`: `<VAR>=<valeur> git push` est refusé.
- `test_shell_keywords_are_skipped`: `then`, `do`, `else`, `{`, `!` devant `git push` sont refusés.
- `test_cmd_and_powershell_are_unwrapped`: `cmd /c`, `powershell -Command`, `pwsh -c` suivis de `git push` sont refusés.
- `test_reads_behind_an_assignment_still_pass`: `<VAR>=<valeur> git status` passe.

**C-02 — Le garde d'`Host` et d'`Origin` de l'API** (S-02, S-18) — `fix`.
`main.py`, `auth.py`.
- `test_foreign_host_is_refused`: `Host` hors `127.0.0.1`, `localhost` et l'hôte déclaré → 403, `STATIC_TOKEN` vide.
- `test_foreign_origin_websocket_is_closed`: handshake WebSocket d'un `Origin` étranger fermé avec un code de la plage 4000-4999.
- `test_listed_origin_and_missing_origin_pass`: l'origine du frontend et un client sans `Origin` (outils, tests) passent.
- `test_health_stays_open`.
- Décision à écrire dans le ticket : l'hôte déclaré vient d'un réglage `ALLOWED_HOSTS`, défaut loopback.

### HIGH

**C-03 — Le garde git/gh devient une liste blanche de lectures** (S-03, S-04, S-05, S-12) — `refactor`.
Voir ADR-067. `git_guard.py`.
- `test_unlisted_git_subcommand_is_refused`: `bisect`, `credential`, `commit-tree`, `symbolic-ref`, `update-index`, `gc`, `notes`, `init`.
- `test_git_config_override_is_refused_unless_cosmetic`: `-c core.fsmonitor=…` refusé, `-c color.ui=false` passe (test existant conservé).
- `test_git_output_option_is_refused`: `--output=<chemin>`.
- `test_gh_global_option_does_not_hide_the_subcommand`: `--repo <o/r> pr merge`, `-R`.
- `test_gh_unlisted_subcommand_is_refused`: `auth token`, `alias`, `secret`, `issue`, `run`; `gh auth status` passe.
- `test_allowlist_keeps_status_diff_log_show`.

**C-04 — Le `.env` de Tessera et les manifestes voisins se refusent en écriture** (S-07, S-08) — `fix`.
`chemins_proteges.py`.
- `test_write_to_the_tessera_env_is_refused_under_ancestor`: `Write` et redirection Bash.
- `test_a_sibling_project_manifest_is_refused_under_ancestor`.
- `test_the_pre_push_hook_script_is_refused`.
- `test_project_own_env_and_fixtures_still_pass`.

**C-05 — `fs.py` applique les chemins protégés et borne les racines de lien** (S-09) — `fix`.
`routers/fs.py`, `project_importer.py`. Dépend de C-04.
- `test_fs_write_to_git_hooks_is_refused`, `…_to_agents_json`, `…_to_github_workflows`, `…_to_claude_settings`.
- `test_symlink_import_root_is_listed_and_bounded`: `_workspace_roots` ne dépasse pas ce que le ticket de produit autorise (§2, question ouverte).
- `test_read_of_a_protected_file_is_still_allowed`.

### MEDIUM

**C-06 — Les formes de redirection collées et `cp`/`mv`/`rm`** (S-11) — `fix`. `redirections_bash.py`.
- `test_glued_redirection_is_a_target`: `echo x>../f`, `2>../f`.
- `test_every_tee_argument_is_a_target`.
- `test_cp_mv_rm_targets_outside_the_root_are_refused`.
- `test_windows_backslash_path_is_not_eaten`.

**C-07 — Le filet d'interpréteur couvre `node -e` et le mode nommé** (S-10) — `fix`.
- `test_node_e_write_to_a_protected_file_is_refused`; `test_python_open_with_named_mode_is_refused`.

**C-08 — Le garde-jetons lit les globs et les dossiers entiers** (S-13) — `fix`.
- `test_bash_glob_reaching_the_env_is_refused`; `test_grep_on_a_directory_holding_the_env_is_refused`; `test_listing_a_folder_still_passes`.

**C-09 — Les captures n'envoient le jeton qu'à l'origine déclarée du projet** (S-14) — `fix`.
- `test_session_token_is_withheld_from_a_foreign_host`; `test_loopback_url_still_receives_it`.

**C-10 — Les noms protégés se comparent sans casse** (S-16) — `fix`.
- `test_protected_names_ignore_case`; `test_neighbours_still_pass`.

**Ticket-677 (existant, todo)** porte S-17 : un seul exécuteur git, hooks désarmés. À ajouter à ses critères : `test_every_git_runner_disables_hooks`.

### LOW

**C-11 — Durcissements** (S-19, S-20, S-21) — `chore`.
- `test_access_log_does_not_show_the_ws_token`; `test_clone_url_with_a_trailing_newline_is_refused`; `test_clone_never_writes_a_token_into_the_remote_url`; bornes de taille sur `SignalementCreate` (`test_signalement_over_the_size_limit_is_refused`).
