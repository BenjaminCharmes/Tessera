# Un worktree par run — conception

Ticket-494, ADR-056. Aucun code : ce document fixe les interfaces et les
contraintes, les tickets 519 à 525 les implémentent.

## Le problème

Un run change de branche et écrit dans le checkout du projet. Sur ide-core
(`git_root: ancestor`) ce checkout est celui où travaillent aussi les sessions
humaines. Le 16/10 :

- une session s'est ouverte sur une branche de ticket aux fichiers modifiés par
  le pipeline ;
- un ticket écrit à la main dans `tickets/todo/` pendant un run a été commité par
  le rangement du pipeline dans la PR du ticket en cours (#508) ;
- un redémarrage du PC a laissé le checkout sur une branche de run.

`RunLock` (ADR-038) protège deux runs entre eux, pas un run d'un humain.

## Contraintes tirées des essais passés

| Accident | Contrainte |
|---|---|
| 14/10 : une jonction `node_modules` dans un worktree a vidé celui du dépôt | Un lien se retire **avant** toute suppression récursive, et un test vérifie que la cible survit |
| Le hook d'écriture (ADR-031) ne suit pas les liens | Les deux côtés se résolvent : une écriture à travers un lien sort de la racine, donc se refuse. Un lien est en lecture seule pour les outils fichier |
| `uv` refusé dans un worktree par le contrôle d'applications | `worktree.env` et `worktree.test_command` : l'interpréteur du `.venv` principal et `PYTHONPATH` se déclarent |
| Chemins longs de Windows | `core.longpaths=true` sur **chaque** appel git, et un dossier racine court |
| `.env`, `CLAUDE.md` et ignorés absents d'un worktree neuf | `worktree.populate` |

## 1. Où vivent les worktrees, leur nom, leur fin

- **Racine** : `IDE_WORKTREES_DIR` (réglage de `config.py`, défaut
  `~/.tessera/worktrees`). Hors de tout dépôt : rien à exclure (ADR-021), rien
  qu'un `git add` puisse balayer. Garder ce chemin court est un conseil de
  `docs/configuration.md`, pas une garantie : la garantie est `core.longpaths`.
- **Dossier** : `<IDE_WORKTREES_DIR>/<project_id>/<ticket_id>`, par exemple
  `.../ide-core/ticket-519`. Un run par ticket et par projet (voir §5) : le nom
  est unique sans horodatage.
- **Branche** : celle du ticket (`ticket-519-<slug>`), **extraite** dans le
  worktree (`git worktree add -b <branche> <dossier> origin/<base>`, ou sans
  `-b` si la branche existe déjà : reprise d'un run, ticket-208). Git refuse une
  même branche dans deux worktrees : si un humain l'a extraite dans le checkout,
  le run est `blocked` avec la cause, il ne force rien.
- **Base** : `fetch` de `origin/<base>`, puis fork de `origin/<base>`. Le checkout
  de l'humain n'est ni lu ni déplacé ; la branche locale `<base>` n'est pas
  avancée par un run. Un fichier écrit à la main dans le checkout n'existe pas
  dans le worktree : c'est ce qui ferme l'accident de #508.
- **Création** : sous `RunLock`, avant `ensure_clean_tree`. Un worktree resté
  d'un run précédent du même ticket est repris s'il est propre et sur la bonne
  branche, sinon traité comme un orphelin (§ suivant).
- **Suppression** : à la fin de la phase 1 de livraison (rebase, push, PR —
  ADR-051), ou à la sortie du run s'il n'est pas livré, **après** le commit final
  (ADR-018, ADR-037). Elle précède `run_closed` pour que le projet ne soit
  libéré qu'une fois le dossier parti. La phase 2 (`CIWatcher`) ne lit ni
  n'écrit aucun arbre : le ticket-519 le vérifie. Si le worktree porte du travail
  non commité après le commit final (commit raté), **il reste**, le run est
  `blocked`, la cause nomme le dossier. On ne détruit jamais ce qu'on n'a pas
  sauvé.
- **Orphelin après redémarrage** : au démarrage, après `solder_les_runs_orphelins`,
  chaque `<IDE_WORKTREES_DIR>/<projet>/<ticket>` sans run vivant (le
  `RunRegistry` est vide au démarrage) est repris : s'il est sale, commit
  `chore: … — unapproved work (run interrupted by a backend stop)` comme
  `reprise_orphelin` (ADR-018 : l'arbre ne reste jamais sale), puis suppression ;
  sinon suppression directe ; `git worktree prune` pour un enregistrement dont le
  dossier a disparu. Le checkout de l'humain n'est jamais touché : l'accident du
  redémarrage ne peut plus se produire. `reprise_orphelin` actuel reste pour les
  projets qui ne déclarent pas `worktree`.

## 2. Ce que le projet déclare

Clé `worktree` de `agents.json`, **lue une fois** avec le reste de
`PolitiqueRun` (ticket-119) — la copie du worktree, que le codeur peut éditer,
n'est jamais relue :

```json
"worktree": {
  "populate": [
    {"path": "CLAUDE.md", "mode": "copy"},
    {"path": "backend/.venv", "mode": "link"},
    {"path": "frontend/node_modules", "mode": "link"}
  ],
  "env": {"PYTHONPATH": "{worktree}/backend/src"},
  "test_command": "{repo}/backend/.venv/Scripts/python.exe scripts/verifier.py"
}
```

Signatures attendues (`models/worktree_config.py`) :

```python
class EntreePopulate(BaseModel):   # frozen
    path: str                      # relatif à la racine du dépôt, sans `..`
    mode: Literal["copy", "link"]

class ConfigWorktree(BaseModel):   # frozen
    populate: tuple[EntreePopulate, ...] = ()
    env: Mapping[str, str] = {}
    test_command: str | None = None   # remplace `test_command` dans le worktree

# PolitiqueRun.worktree: ConfigWorktree | None  — None : le run reste dans le checkout
```

Placeholders : `{worktree}` (racine du worktree), `{repo}` (checkout du
dépôt, d'où viennent les liens). Aucun autre.

Règles, toutes fermées :

- **Clé absente ou illisible : le run reste dans le checkout.** Cette conception
  ne change le comportement d'aucun projet qui ne déclare rien. Retourner le
  défaut vers le worktree est une décision à part (voir « Ce que ça ne tranche
  pas »).
- **`copy`** pour tout ce que le run peut éditer ; **`link`** seulement pour ce
  que git **ignore** (`git check-ignore`), jamais pour du suivi. Une entrée
  `link` non ignorée est refusée et journalisée.
- Un chemin absolu, avec `..`, ou qui résout au `.env` de Tessera, est refusé
  (ADR-053 : un agent ne lit pas ce fichier ; le copier dans un dossier où il
  écrit le lui rendrait lisible). Le `.env` **d'un projet** se copie : c'est le
  sien, pas celui de Tessera.
- **Entrée absente dans le checkout** : journalisée (`worktree_populate_manquant`,
  chemin nommé), jamais bloquante. Les tests diront ce qui manque.
- **Un `mode` inconnu retire l'entrée**, il ne devine pas `link`.
- **Suppression** : les liens se retirent d'abord (`os.rmdir` sur une jonction,
  `os.unlink` sur un lien symbolique, détectés par l'attribut de point d'analyse
  sous Windows), puis le dossier. `git worktree remove --force` et `rmtree` ne
  s'exécutent qu'**après**, et seulement si plus aucun lien n'y est. C'est la
  correction directe de l'accident du 14/10.
- Les artefacts du projet (`tickets/`, `memory/`, `CLAUDE.md`) viennent du dépôt
  quand le mode est `tracked` : rien à peupler. `CLAUDE.md` figure dans l'exemple
  parce qu'un `CLAUDE.md` ignoré par git n'y serait pas.

## 3. `git_root: ancestor`, `test_command`, le hook

- **`git_root: ancestor` change de sens, pas de forme.** Il désignait « le run
  travaille dans le dépôt qui contient le projet ». Il désigne désormais « le
  worktree est celui de ce dépôt ». Le dossier du projet dans le worktree est
  `<worktree>/<chemin du projet relatif à la racine du dépôt>` ; pour un projet
  qui est la racine de son dépôt, c'est la racine du worktree.
- **Ce qui se lit sur le dossier réel, ce qui se lit dans le worktree.** La
  politique (`PolitiqueRun`) se lit sur le **dossier réel** du projet : jamais
  d'`agents.json` du worktree. Tout le reste — `TicketService`,
  `pipeline_log_path`, `GitWorkspaceService`, `cwd` des agents, `carte_du_depot`
  — reçoit le dossier du projet **dans le worktree**.
- **Hook d'écriture (ADR-031)** : `racine_ecriture` devient le worktree (ancestor)
  ou le dossier du projet dans le worktree. La résolution des symlinks des deux
  côtés est conservée : c'est elle qui rend un lien en lecture seule. Un test le
  fige (écriture via `node_modules` liée : refusée).
- **`ADR-024`** : `rev-parse --show-toplevel` se vérifie sur le dossier réel
  avant la création du worktree ; dans le worktree, il renvoie sa racine, et
  `_ensure_own_repository` doit l'accepter sans passer par `ancestor`.
- **`CLAUDE.md` des ancêtres** : `claude_md_ancetres_a_exclure` calcule depuis
  `_REPO_ROOT`. Un worktree est **hors** de ce dépôt : le calcul s'appuie sur
  `racine_ecriture`, pas sur `_REPO_ROOT`. Le ticket-525 le règle.
- **`test_command` et `test_cwd`** : `test_cwd` est relatif au dossier du projet
  *dans le worktree*. Si `worktree.test_command` est déclaré, il remplace
  `test_command` ; `worktree.env` s'ajoute à l'environnement de la commande
  (`TestRunnerService` gagne un paramètre `env`). `controles_depart` vérifie le
  premier mot de la commande **effective**. Le script que la commande lance se
  refuse en écriture comme aujourd'hui (ADR-027), résolu dans le worktree.
- **Les tests ne passent plus par `uv`** dans un worktree : pas de contournement,
  c'est ce que `worktree.test_command` déclare.

## 4. Ce que l'interface n'a plus

- Le tableau lit le checkout : un ticket en cours y reste `todo` jusqu'au merge
  de sa PR, puisque son déplacement en `in-progress` se commite sur la branche.
  `RunRegistry` dit ce qui tourne. C'est le prix de ne plus écrire dans le
  checkout, et il se paie à l'écran, pas dans les données.
- Le chat (ADR-019) écrit toujours dans le checkout : hors de ce ticket.

## 5. `RunLock`

**Il reste, par projet.** Le worktree retire la raison *arbre partagé*, pas les
autres :

- ADR-051 : le ticket N+1 forke depuis `origin/<base>` et lui faut le merge de N ;
  deux runs parallèles du même projet livreraient sur une base qui bouge ;
- les services de test (ports, bases) et le quota (ADR-020) sont partagés ;
- le verrou doit refuser bruyamment, pas empiler (ADR-038).

Ce qui change : la phrase d'ADR-038 « deux runs sur le **même** arbre » devient
« sur la même base ». Le worktree est la **condition** d'un futur parallélisme,
pas sa décision. Quand elle se prendra, la clef du verrou passera de
`project_id` à `(project_id, ticket_id)`, et le nom du dossier le permet déjà.

## 6. Découpage

| Ticket | Contenu | Dépend de |
|---|---|---|
| 521 | `ConfigWorktree`, `PolitiqueRun.worktree`, `IDE_WORKTREES_DIR` | — |
| 522 | `RunWorktree` : créer, reprendre, supprimer, `core.longpaths` | — |
| 523 | `populate`, liens, suppression sûre | 521, 522 |
| 524 | `test_command` effective et `env` dans un worktree | 521 |
| 525 | Hook d'écriture, ADR-024 et `CLAUDE.md` d'ancêtres suivent le worktree | 521 |
| 519 | Exécution dans le worktree : orchestrateur, fin de run | 521 à 525 |
| 520 | Reprise des worktrees orphelins au démarrage | 522, 523 |

Les numéros 515 à 518 étaient déjà pris par des tickets livrés : l'ordre
numérique ne suit donc pas l'ordre de dépendance, seul `depends_on` fait foi.

## Ce que ça ne tranche pas

- **Retourner le défaut vers le worktree.** Il faut d'abord qu'ide-core l'ait
  éprouvé ; c'est un choix de l'humain.
- **Les projets en `artifacts: local`.** Leurs `tickets/` et `memory/` ne sont
  pas dans git : un run dans un worktree devrait les copier puis les **rapatrier**
  dans le checkout, avec un cas de conflit si l'humain les a modifiés entre-temps.
  Un `worktree` déclaré sur un projet `local` est **refusé** avec une raison
  claire, pas contourné. À concevoir avant d'ouvrir ce cas.
- **Le chat** et le **parallélisme** de deux runs (§ 4 et 5).
- **L'activation sur ide-core** : `agents.json` se refuse en écriture aux agents
  (ADR-027). Un humain y ajoute la clé `worktree` quand les tickets 519 à 525
  sont mergés.
