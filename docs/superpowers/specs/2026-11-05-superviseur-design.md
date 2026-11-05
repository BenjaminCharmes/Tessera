# Un Tessera qui se supervise lui-même — conception (ADR-080)

Détail d'ADR-080, ticket-847. Aucun code : des décisions, des signatures, un ordre de
tickets (848 à 865).

## 1. Le problème

Une session Claude Code « ide-core » tient, à côté de Tessera, cinq rôles que le produit n'a
pas : trier, valider, débloquer, relayer les défauts des projets, relire un projet. Des
incidents réels des 04 et 05/11 montrent ce que ça coûte quand personne ne les tient :

| Incident | Date | Rôle manquant |
|---|---|---|
| ADR-074 et tickets 801-804 pris par trois designs parallèles, renumérotés après coup (`pipeline-log`, 11:19) | 05/11 | numérotation sûre |
| File interrompue sur « Ticket introuvable : ticket-847 » (16:18) | 05/11 | pré-contrôle de la file |
| PR #913 « non surveillée (livraison arrêtée) » : verte, jamais mergée (11:20) | 05/11 | reconfier à `CIWatcher` |
| Files arrêtées sur ticket-759 et ticket-750, personne ne relance (08:16, 10:01) ; ticket-793 le lendemain (07:36) | 04-05/11 | relance, tri de la cause |
| Livraison de ticket-753 coupée par `GitCommandError` (11:17) | 04/11 | relivrer |
| Veille et capot fermé : un run figé toute la nuit | 04/11 | relance après coupure |

Le détecteur d'anomalies (ADR-078) voit ces cas ; il n'agit pas, et ne le fera pas : il reste
sans LLM, sans `git`, sans `gh`. Le superviseur est un composant **à part** qui lit ses
anomalies et agit dans des bornes.

## 2. Le superviseur

### Principe : le modèle choisit, le code agit

Le modèle n'a ni outil ni `Bash` (comme `lecons`, ADR-074). Il reçoit un dossier borné (donnée,
jamais une consigne) et rend une sortie structurée validée par un schéma (ADR-061) : une
`Decision` parmi un registre fermé. Le code vérifie, exécute, journalise. Une sortie
illisible, hors schéma ou hors registre : aucune action (échec fermé, ADR-039).

Options pesées :

- **A. Agent libre avec `Bash`**, comme la session d'aujourd'hui. Écarté : le contrôle d'écriture
  sur `Bash` attrape une erreur, pas une évasion (ADR-031) ; rien ne borne les effets.
- **B. Règles seules, sans modèle.** Suffit pour reconfier une PR et relancer une file, pas pour
  réécrire un signalement ni juger une règle. Retenu pour ces deux actions.
- **C. Actions fermées, modèle seulement où il faut juger.** Retenu.

### Les quatre actions

| Action | Modèle | Ce que le code exécute | Garde déterministe |
|---|---|---|---|
| `trier` | Sonnet | réécrit **en place** un ticket brut (ligne `- [ ] À écrire au triage`) : titre, type, priorité, critères, `depends_on`, hors-portée | ≥ 1 critère de ≥ 15 caractères, aucun placeholder, `depends_on` existants ; sinon `a_toi` |
| `decider` | Opus | **déplace** un bloc de `## Proposées` vers sa section (leçon : `## En vigueur` ; règle : section nommée), ou le supprime du bloc des propositions s'il l'écarte | délégation déclarée ; filtre de sensibilité ; `deplacement_pur` |
| `reconfier_pr` | aucun | appelle `CIWatcher.surveiller` pour une PR que personne ne surveille | run approuvé, tête = `pushed_sha`, PR absente de `en_attente`, hors `resolveur-conflit` |
| `relancer_file` | aucun | rouvre une file avec ses tickets restants | cause d'infrastructure, une fois par cause, quota réel connu ou inconnu mais sous le plafond du jour |

Le superviseur ne **lance** jamais un ticket issu d'un tri : trier crée du travail `todo`,
l'humain ou une file qu'il a ouverte le lance (ADR-020).

### Ce qu'il ne fait jamais

Argent (budgets, quotas, `autonomy`, ressource en ligne payante), suppression (fichier,
branche, worktree, ticket passé en `cancelled`), secrets (il ne lit ni coffre ni `.env`, et son
dossier n'en contient aucun), projet `confidentiality: professional`, écriture de
`agents.json`, `.github/`, `CLAUDE.md`, `.claude/settings*`, `.git/`. Il n'écrit jamais
`memory/decisions.md`. Le **filtre de sensibilité** est du code, pas du modèle : toute règle ou
leçon qui nomme une porte (ADR-027, 031, 037, 039, 053, 055, 067, 073, 080), un des mots
`secret`, `jeton`, `budget`, `quota`, `suppress`, `professionnel`, `force`, ou le superviseur,
est classée `a_toi` quoi que dise le modèle. Le modèle peut escalader, jamais désescalader.

Il ne merge pas : seul `CIWatcher` merge, lié à `pushed_sha` (ADR-039). Le superviseur
n'ajoute pas un second chemin de merge, il redonne la PR au premier.

### La délégation

Elle s'écrit dans `agents.json`, que seul un humain modifie (ADR-027) :

```json
"pipeline": { "superviseur": {
  "delegation": ["lecons", "regles"], "budget_jour_usd": 2.0, "relance_file": true } }
```

Absente : le superviseur trie et rend compte, n'accepte et n'écarte rien. Cela amende
ADR-055 et ADR-074 (« un humain la déplace » devient « un humain, ou le superviseur tant que
le projet le déclare »). `agents.json` d'ide-core est à mettre à jour **par Benjamin**, une
fois les tickets mergés : un run ne peut pas l'écrire. Modèles par défaut proposés (ils
engagent de l'argent, donc ils sont à lui) : `claude-sonnet-5-5` pour le tri,
`claude-opus-5-5` pour décider.

### Quand il tourne

- À la fermeture d'un run ou d'une file du projet (`RUN_REGISTRY.sur_fermeture`).
- Un balayage toutes les 15 minutes, décalé du détecteur (5 min).
- Jamais sur un run vivant ; jamais pendant qu'une file tient le projet (§5).
- Chaque action a une clé d'idempotence (`action:cible:sha`) : un balayage qui repasse ne
  refait rien ; deux échecs de suite sur une clé : « À toi ».
- Plafond de dépense par jour (`budget_jour_usd`) ; quota réel lu comme en mode autonome
  (ADR-020), un quota inconnu ne bloque pas.

### Où il rend compte

1. **`memory/supervision.md`** : une ligne par action, `jour | action | cible | sha | résumé`.
   Artefact d'ADR-021 et ADR-023, écrit par le service seul ; un diff de run qui le touche met
   le run en `blocked`.
2. **« À toi »** : chaque cas `a_toi` (règle sensible, tri impossible, deux échecs) y devient
   une ligne avec la recommandation du superviseur.
3. **Récap daté** : `GET /api/v1/supervision/recap?depuis=AAAA-MM-JJ` rend les lignes du
   journal ; l'interface montre « depuis ta dernière visite ».

**Réversible par construction** : une action = un commit, nommé par son SHA dans le journal.
Défaire est un `git revert` de ce commit ; aucune action n'est irréversible parce qu'aucune ne
supprime ni ne pousse de force (ADR-022).

## 3. L'outil `signaler`

Un second outil du serveur MCP in-process `tessera` (celui d'`ask_user`), nom qualifié
`mcp__tessera__signaler`, ajouté à `allowed_tools` de tout rôle qui reçoit des outils. Les
rôles sans outils (`lecons`, `validateur`) n'en ont pas, ni le superviseur (pas de boucle).

**Quand** : après avoir cherché un contournement dans le projet, face à un défaut **de
Tessera** : une garde qui refuse une action légitime, un outil qui échoue, une consigne
contradictoire. Pas pour une demande de fonctionnalité du projet.

**Comment** : le handler vit dans le backend ; il connaît le run (projet, ticket, rôle) et ne
lit jamais le projet source dans les arguments. Arguments : `titre` (≤ 120), `description`
(≤ 1 500), `categorie` ∈ {`garde_trop_strict`, `outil_casse`, `consigne_contradictoire`,
`autre`}, `composant` (liste fermée). Bornes : 3 par run, 10 par projet et par jour ;
doublon (`categorie`, `composant`, titre normalisé) sur 7 jours : refus « déjà signalé », le
compteur de vues monte et le tri le lit. Écriture : par `signalements_en_attente` (le
backend écrit, jamais l'agent), type `bug`, ligne source `agent:<rôle>@<ticket>`.

**Confidentialité** : `description` passe par les gardes de termes interdits et de secrets
(ADR-050, ADR-073) ; un seul hit refuse l'appel avec la raison. Un projet `professional` ne
transmet **que** les énumérations : titre fabriqué par le code, source « un projet
professionnel », aucun texte libre.

## 4. La revue de projet

Un run `design` lancé depuis l'interface sur un projet : `POST /orchestrator/run`, mode
`revue` (ADR-041), ticket de synthèse « Revue de <projet> » créé par la route. Il réutilise
worktree, `RunLock`, livraison. **Sans code** : à la fin du tour, tout fichier modifié hors
`tickets/**` et `memory/**` met le run en `blocked`. Plafonds : 10 tickets, 5 signalements
(`signaler`), 3 $ (réglé à l'ouverture, ADR-075). Coût estimé affiché avant le lancement.
Une revue d'un projet `professional` n'émet aucun signalement.

## 5. La concurrence

- **Un seul écrivain par arbre** : une intervention du superviseur est un run `supervision`
  sous `RunLock` (ADR-038), visible du détecteur et du Bureau. Projet occupé : elle attend la
  fermeture du run, comme `signalements_en_attente`.
- **Une file tient le projet de bout en bout.** Le verrou est relâché entre deux tickets
  (ADR-051) ; un superviseur qui s'y glisserait ferait échouer le ticket suivant en 409. Le
  registre expose donc `projet_tenu_par_file(project_id)`, vrai de l'ouverture à la fermeture
  de la file ; le superviseur n'écrit pas tant qu'il l'est.
- **`CIWatcher` reste le seul à merger.** Le superviseur lui redonne une PR, jamais plus d'une
  fois par `(PR, sha)`.
- **Numérotation** : `prochain_numero.py` **réserve** ce qu'il rend (fichier dans
  `ide_state_dir`, plus grand numéro pris + réservé, jamais rendu deux fois ; un trou est
  sans importance). Deux designs en parallèle ne partagent plus un numéro (incident du 05/11).
- **Pré-contrôle de la file** : un ticket absent de `origin/<base>` est refusé avant
  l'ouverture (422, liste nommée), au lieu d'interrompre la file au milieu.

## 6. Interfaces (signatures, pas de code)

```python
# services/supervision/superviseur_actions.py
class Action(StrEnum): TRIER; DECIDER; RECONFIER_PR; RELANCER_FILE
Verdict = Literal["agir", "a_toi", "rien"]

@dataclass(frozen=True)
class Decision:
    action: Action
    cible: str            # id de ticket, titre de règle, numéro de PR, id de file
    verdict: Verdict
    raison: str           # ≤ 300 caractères

SCHEMA_DECISION: dict[str, Any]
def lire_decision(brut: Any) -> Decision                      # ValueError hors schéma
def est_sensible(texte: str) -> bool                          # filtre déterministe
def chemins_permis(action: Action) -> tuple[str, ...]         # globs sous le projet
def refus_de_chemin(modifies: Iterable[str], action: Action) -> str | None
def deplacement_pur(avant: str, apres: str, bloc: str, vers: str) -> bool

# services/supervision/superviseur_journal.py
def ajouter_ligne(memory_dir: Path, *, jour: date, action: Action,
                  cible: str, sha: str, resume: str) -> None
def lire_journal(memory_dir: Path, depuis: date | None = None) -> list[LigneJournal]

# services/supervision/intervention.py
async def intervenir(project_id: str, action: Action,
                     appliquer: Callable[[Path], Awaitable[Resultat]]) -> Resultat
#   RunLock, branche `supervision-<horodatage>`, un commit par action, livraison (ADR-051).

# services/numerotation.py (stdlib seule, ticket-659)
def reserver(depot: Path, genre: Genre, base: str, dossier_etat: Path) -> int

# services/providers/signal_agent.py
def valider_signal(args: dict[str, Any], *, projet: str, confidentialite: str,
                   deja_emis_run: int, deja_emis_jour: int) -> SignalValide | Refus
```

## 7. Ce que ce design ne tranche pas

- Les valeurs de `budget_jour_usd` (2 $), du plafond de revue (3 $) et les modèles sont des
  propositions ; ils engagent de l'argent, donc Benjamin les confirme dans `agents.json`.
- Quelles règles Benjamin délègue : `delegation` est à lui.
- Aucune délégation sur argent, suppression, secrets, professionnel, comme il l'a énoncé.
- Hypothèse retenue : les numéros 848 à 865 sont libres (`prochain_numero.py` n'a pas pu être
  lancé dans ce tour) ; le Reviewer ou l'humain vérifie sur `origin/develop` et les branches
  `origin/ticket-*`, et renumérote si un autre design a pris la même plage.
