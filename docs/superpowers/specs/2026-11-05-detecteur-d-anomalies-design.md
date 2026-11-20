# Détecteur d'anomalies des runs — conception

Ticket-774, ADR-073. Aucun code n'est écrit par ce document : il fixe les règles, les
seuils, les contrats et le découpage en tickets 794 à 833.

## Le problème

Tessera n'a qu'un indicateur, « figé ? » (`frontend/src/lib/santeAgent.ts`, ticket-549), et
il est calculé dans le navigateur, sur l'écart au dernier événement. Il a trois trous :

- Il exempte les étapes silencieuses (`tests`, `securite`, `validation`, `documentation`,
  `livraison`), qui n'émettent rien pendant qu'elles travaillent (ticket-587). Un testeur
  figé y reste « silencieux » à jamais : c'est le testeur du 03/11, figé de 19 h à 7 h 48.
- Il ne dit rien d'un run qui avance mais tourne en rond : trois tours perdus sur des doubles
  de test le 03/11.
- Il ne voit qu'un run, à l'instant T. Deux livraisons coupées par le réseau le 03/11 étaient
  deux runs distincts, chacun « normal » pris seul.

Trois autres arrêts existent déjà et restent : `agent_silence_max_s` (20 min, coupe un agent
muet), `test_timeout_s` (coupe la suite de tests) et `run_max_budget_usd` (entre deux tickets,
ADR-020). Ce sont des **gardes** : ils agissent. Le détecteur est un **témoin** : il dit.

## Options

1. **Témoin dans le backend, tâche de fond, lecture seule** — retenue. Il voit les runs même
   onglet fermé, lit l'historique pour ses médianes, et ne peut rien casser.
2. **Étendre `santeAgent.ts`** — écartée. Pas d'historique côté navigateur (donc ni médiane,
   ni blocages consécutifs), et rien ne se signale quand l'onglet est fermé : la nuit du 03/11
   était justement sans observateur.
3. **Règles dans le pipeline, qui coupent le run** — écartée. Un faux positif jetterait un
   travail déjà payé (ADR-037), et chaque seuil se règlerait contre un run réel. Rouvrir quand
   un seuil aura tenu 30 runs sans faux positif ; ce serait alors une ADR à part.

## Les règles

Toutes de gravité `warning`, toutes sur le **ticket courant** d'un run vivant. Les seuils
sont des réglages de `config.py` (`anomalie_*`), pas des constantes.

| Règle | Se déclenche quand | Donnée lue | Clé de dédoublonnage |
|---|---|---|---|
| `outil_repete` | une série d'au moins **4** `agent_tool_use` consécutifs du même agent, même `tool`, même `input` | `agent_events` du ticket, depuis le dernier `agent_started` | `outil_repete:<id du premier appel de la série>` |
| `etape_longue` | une étape ouverte dure plus de `max(3 × médiane, 5 min)`, médiane des **20** dernières étapes closes du même projet et de la même étape, **10** échantillons au moins | paires début/fin de `agent_events` | `etape_longue:<étape>:<ts du début>` |
| `silence` | aucun événement, tokens compris, depuis **15 min** | `RunActif.dernier_evenement_a` | `silence:<dernier_evenement_a>` |
| `cout_anormal` | coût du ticket `> max(3 × médiane, 0,50 USD)` (20 derniers runs `single` finis du projet, 10 au moins), **ou** run `autonomous` à `≥ 80 %` de `run_max_budget_usd` | `agent_calls`, `RunActif.cout_usd` | `cout_median:<id de la ligne du ticket>` ou `cout_budget:<run_id>` |
| `tours_de_revue` | le tour courant atteint **3** | `RunActif.tour` | `tours:<ticket>` |
| `blocages_identiques` | les deux derniers runs `single` finis du ticket sont `blocked` avec la **même signature** de cause | `pipeline_runs.arret` | `blocages:<id du plus récent>` |

### Ce que la règle dit de plus que le ticket

- **`tours_de_revue` : seuil 3, pas « 3 corrections ».** `max_review_rounds` vaut 3 : un
  quatrième tour n'existe pas, et « 3 corrections » ne se constate qu'à la fin du run. Le
  tour 3 est la dernière tentative, après deux refus : c'est là que le signal sert. Un projet
  qui descend `max_review_rounds` sous 3 n'a jamais cette alerte ; le run s'arrête de lui-même.
- **`silence` n'est pas `etape_longue`.** Dans une étape silencieuse dont la médiane est
  armée (10 échantillons), seul `etape_longue` parle : le silence y est normal. Sans médiane
  (projet neuf), `silence` parle aussi dans l'étape silencieuse : c'est le seul filet, et
  c'est lui qui aurait attrapé le testeur du 03/11 sur un projet sans historique.
- **Exemptions du silence** : une question d'agent en attente (ADR-025) et une attente
  extérieure (`external_wait` à `waiting: true`). Dans les deux cas le silence est voulu.
- **Plancher** : le plus grand de `3 × médiane` et d'un minimum absolu (5 min, 0,50 USD).
  Sans lui, un audit médian à 20 s alerterait à 60 s.
- **`cout_budget` ne vaut qu'en `autonomous`**, là où ADR-020 s'applique. Le signal arrive
  en cours de ticket : ADR-020 interdit d'**interrompre** au milieu d'un ticket, pas de le
  dire.
- **Signature d'un blocage** : première ligne de `arret`, en minuscules, nombres, hexadécimaux,
  chemins et chaînes entre guillemets remplacés par un marqueur, coupée à 120 caractères. Un
  `arret` vide ne compte pas. Le ticket qui l'écrit se valide sur deux vrais `arret` de
  livraison coupée par le réseau.
- **Jamais le contenu d'un outil.** Le message nomme l'outil, jamais son `input` : un
  `Write` ou un `Bash` peut porter un chemin, un jeton, un secret (ADR-053).

### Les étapes

Une étape se lit dans les événements déjà persistés, sans événement de plus :

| Étape | Début | Fin |
|---|---|---|
| `codeur`, `architect`, `reviewer`, … | `agent_started` de cet agent | `agent_done` de cet agent |
| `tests` | `test_started` | `test_result` |
| `securite` | `security_audit_started` | `security_audit_done` |
| `validation` | `validation_started` | `validation_done` |
| `documentation` | `documentation_started` | `doc_updated` ou `documentation_failed` |
| `livraison` | `livraison_started` | `livraison_done` |

Un début rouvert par un nouveau début de la même étape, sans fin entre les deux, est une
étape abandonnée : ni mesure, ni échantillon. Une étape jamais close — le testeur figé —
n'entre donc pas dans la médiane qui la jugera.

## Les contrats

Le dossier est `backend/src/tessera/services/anomalies/`, un fichier par responsabilité.

```python
# modeles.py
Regle = Literal["outil_repete", "etape_longue", "silence",
                "cout_anormal", "tours_de_revue", "blocages_identiques"]

class Anomalie(BaseModel):
    regle: Regle
    cle: str                      # clé de dédoublonnage, voir le tableau
    ticket_id: str
    message: str                  # français, 200 caractères au plus, sans `input` d'outil
    mesure: float
    seuil: float
    unite: Literal["appels", "s", "usd", "pourcent", "tours", "runs"]
    etape: str | None = None
    agent: str | None = None

# regles_directes.py — pures, sans I/O ni horloge (le « maintenant » est un paramètre)
def outil_repete(appels: Sequence[AppelOutil], seuil: int = 4) -> Anomalie | None: ...
def silence(dernier: datetime | None, maintenant: datetime, *,
            seuil_s: float = 900.0, exempte: bool = False) -> Anomalie | None: ...
def tours_de_revue(tour: int, ticket_id: str, seuil: int = 3) -> Anomalie | None: ...

# regles_historiques.py — pures
def mediane_si_assez(echantillon: Sequence[float], minimum: int = 10) -> float | None: ...
def etape_longue(etape: Etape, maintenant: datetime,
                 passees_s: Sequence[float], plancher_s: float = 300.0) -> Anomalie | None: ...
def cout_anormal(cout_usd: float, passes_usd: Sequence[float], *, plancher_usd: float = 0.5,
                 cumul_usd: float | None = None, budget_usd: float | None = None) -> Anomalie | None: ...
def blocages_identiques(derniers: Sequence[RunFini]) -> Anomalie | None: ...
def signature_d_arret(arret: str | None) -> str | None: ...

# etapes.py — pure
def etapes_depuis(evenements: Sequence[EvenementLu]) -> list[Etape]: ...   # ouvertes et closes

# lecture_evenements.py et lecture_historique.py — les seuls fichiers qui touchent SQLite,
# en lecture. Le premier lit un ticket, le second l'historique d'un projet.
async def derniers_appels_d_outils(db_path, run_id, ticket_id, n: int = 8) -> list[AppelOutil]: ...
async def evenements_de_etapes(db_path, run_id, ticket_id) -> list[EvenementLu]: ...
async def durees_passees(db_path, project_id, etape: str, n: int = 20) -> list[float]: ...
async def couts_passes(db_path, project_id, n: int = 20) -> list[float]: ...
async def cout_du_ticket(db_path, run_row_id: str) -> float: ...
async def ligne_ouverte_du_ticket(db_path, project_id, ticket_id) -> LigneOuverte | None: ...
async def derniers_runs_finis(db_path, project_id, ticket_id, n: int = 2) -> list[RunFini]: ...

# detecteur.py
class DetecteurDAnomalies:
    def __init__(self, registre: RunRegistry, hub: EventHub, db_path: Path, reglages) -> None: ...
    async def passe(self) -> list[Anomalie]: ...   # une passe, testable sans boucle ni sommeil
    async def boucle(self) -> None: ...            # passe(), puis dort `anomalie_intervalle_s`
```

Ajouts au registre (`RunActif`, `RunRegistry`) :

- `dernier_evenement_a: datetime | None`, posé par `_suivre` à **chaque** événement.
- `attente_exterieure: bool`, posé par `external_wait` (`waiting`).
- `anomalies: list[dict]` — les anomalies signalées, 20 au plus, les plus récentes ; **dans
  `en_dict()`**, pour qu'un client arrivé après coup les voie, comme `question` (ticket-163).
- `anomalies_vues: set[str]` — les clés déjà signalées ; **hors `en_dict()`**.
- `RunRegistry.vivants() -> list[RunActif]`.

Événement : `EventType.RUN_ANOMALY = "run_anomaly"`, `data` = l'`Anomalie` sérialisée.
**Non jetable** dans `EventHub` : c'est une transition d'état, pas du texte.

## Où il tourne

- **Une tâche asyncio du backend**, créée dans le `lifespan` de `main.py` après
  `_reprendre_les_surveillances()`, annulée et attendue à l'arrêt. Pas de processus, pas de
  cron : un run ne vit que dans ce process (ADR-038), et le registre est en mémoire.
- **Cadence 5 min** (`anomalie_intervalle_s = 300`). Les seuils vont de 15 min à 3 × une
  médiane : une passe plus fine ne rattraperait rien. Un `anomalies_actives = False` coupe tout.
- **Une passe lit, ne mute pas.** Elle appelle `RUN_REGISTRY.vivants()`, lit SQLite sans
  écrire, calcule des `Anomalie`. Le seul effet est le signalement (ci-dessous).
- **Il émet par l'`emetteur` existant** (`run_executor.emetteur(EVENT_HUB, run, run_id)`) :
  publication, puis persistance dans `agent_events`, sans second chemin d'écriture. Le
  `run_id` de persistance est celui que l'émetteur du run utilise ; dans une file ce sont les
  événements de l'enveloppe, filtrés par `ticket_id` : le ticket 798 le vérifie sur une file.

### Une seule fois

La clé de l'anomalie entre dans `RunActif.anomalies_vues` **après** l'émission. Une passe qui
retombe sur la même clé n'émet rien. Une clé est un **épisode**, pas une règle : un silence
qui se rompt puis reprend a un autre `dernier_evenement_a`, donc une autre clé ; une série
d'outils qui se rompt puis se reforme a un autre premier appel. L'ensemble meurt avec le
`RunActif` : pas de table, pas de nettoyage, et un redémarrage solde déjà les runs
(`solder_les_runs_orphelins`, ticket-177).

### Ce qu'il ne fait jamais

- Arrêter, relancer, suspendre ou modifier un run, une file, un ticket, un worktree.
- Appeler un LLM, un provider, `git` ou `gh`. Zéro token.
- Écrire dans un dépôt ou dans `memory/pipeline-log.md` : un écrivain hors du run salirait
  l'arbre de base, ce que les tickets 786 et 789 ont dû réparer.
- Faire échouer un run. Une exception dans une passe se journalise
  (`anomalie_passe_en_echec`) et la boucle continue ; un run n'attend jamais le détecteur.
  Ce n'est **pas** une porte qui échoue fermée : c'est un témoin, il échoue **muet** et le dit
  dans le log.

Si la machine a dormi (`veille-fige-les-runs`), la passe suivante arrive très en retard et
voit tous les runs « silencieux ». C'est vrai : ils n'ont pas avancé. La passe le journalise
(`anomalie_passe_tardive`, avec l'écart) pour qu'on lise l'alerte pour ce qu'elle est.

## Où elle s'affiche

| Lieu | Ce qui s'y voit | D'où ça vient |
|---|---|---|
| **Cloche** | une notification de type `anomalie`, réglable par type comme les autres (ticket-554) | `RunActif.anomalies`, nouvelle entrée entre deux instantanés |
| **Fil du run** | une ligne par `run_anomaly` dans l'historique du run | `agent_events`, relu par `GET /runs/{id}/events` |
| **Bureau** | un état `etat-anomalie`, ambre, à l'agent du run | `anomalies` non vide dans l'instantané (ADR-058 : une donnée ou rien) |
| **Salle Tessera** | le nombre d'anomalies à côté de chaque run vivant | `RunVivant.anomalies` |
| **Journal** | une ligne `anomalie_de_run` (règle, ticket, mesure, seuil) | `tessera.log` |

La cloche ne notifie que les anomalies **nouvelles** depuis l'instantané précédent : à la
connexion, celles qui existent déjà sont la base, pas un message. Les couleurs suivent
ADR-026 : ambre pour une attente à vérifier, jamais de violet en texte.

## Ce que cette conception ne tranche pas

- **La calibration.** Les seuils viennent d'un IDE comparable ; les médianes de Tessera
  (une suite de tests à 6 min, un codeur à 8 min) ne sont pas les siennes. Mesure non faite :
  à relire après 30 runs, en comptant les alertes sans suite. Le plancher de 5 min, celui de
  0,50 USD et les 15 min de silence sont mes choix, pas une mesure.
- **Une action automatique.** Aucune règle n'agit. Qu'une anomalie, un jour, puisse couper
  un run est une décision de Benjamin, pas de cette conception.
- **Les projets importés.** La médiane se lit par projet : un projet sans historique n'a que
  `outil_repete`, `silence`, `tours_de_revue`, et `cout_budget`.

## Découpage

Chaque ticket tient en moins d'une journée et nomme ses tests, un au-dessus et un en dessous
de chaque seuil. La chaîne 794 → 799 est linéaire : les tickets 795 à 798 ajoutent chacun aux
mêmes fichiers de lecture, et `depends_on` les range un à un.

| Ticket | Contenu | Dépend de |
|---|---|---|
| 794 | `RunActif` (champs, `en_dict`), `RunRegistry.vivants`, `EventType.RUN_ANOMALY`, modèle `Anomalie`, réglages | — |
| 795 | règles directes : `outil_repete`, `silence`, `tours_de_revue`, lecture des appels d'outils | 794 |
| 796 | étapes, médianes, `etape_longue`, `durees_passees`, index | 795 |
| 797 | `cout_anormal` et lectures de coût | 796 |
| 798 | `blocages_identiques`, `signature_d_arret`, `derniers_runs_finis` | 797 |
| 799 | `DetecteurDAnomalies`, dédoublonnage, `lifespan` | 798 |
| 800 | frontend : type `anomalie` de la cloche, ligne du fil du run | 799 |
| 801 | Bureau : état `etat-anomalie` | 799 |
| 802 | Salle Tessera : nombre d'anomalies par run | 799 |
