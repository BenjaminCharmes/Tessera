# Réglages globaux modifiables depuis l'interface — conception

ADR-075, ticket-780. Aucun code ici : des contrats que les tickets 805 à 810 implémentent.

## 1. Ce qui se modifie, et ce qui ne se modifie jamais

Un réglage entre au registre s'il est **global** (pas par projet), **non secret**, **scalaire**
et **sans effet de sécurité** s'il est mal posé. Cinq y entrent :

| Nom | Type | Min | Max | Effet |
|---|---|---|---|---|
| `run_max_budget_usd` | float | 0,5 | 50 | prochain run |
| `llm_max_budget_usd` | float | 0,25 | 10 | prochain run |
| `dialogue_timeout_s` | float | 30 | 3600 | prochain run |
| `max_parallel_test_runs` | int | 1 | 8 | machine : prochaine acquisition d'un créneau |
| `keep_awake_during_runs` | bool | — | — | machine : prochaine ouverture du premier run |

Les bornes sont **une proposition** : le registre est un tableau, un humain les relit et les
change sans toucher le reste. `0` (« sans plafond », « sans borne ») n'est jamais posé par
l'interface : il ne s'obtient que dans `.env`. Le chemin vers moins de protection reste
un geste d'édition de fichier, pas un clic.

N'entrent jamais : les neuf secrets d'ADR-073 ; tout chemin ou URL (`ide_*_dir`, `ollama_base_url`) ;
`static_token`, `allowed_hosts`, `allowed_origins` (la surface de sécurité de l'API) ; `llm_provider` ;
tout ce qui se déclare par projet dans `agents.json`. Un nom hors registre est un 404, y compris
`static_token` : la route ne confirme même pas qu'il existe.

Écartés pour l'instant, faute de besoin constaté : `chat_max_conversation_usd` (même famille que
`run_max_budget_usd`, s'ajoute d'une ligne au registre) et les plafonds de tours `llm_max_turns*`.

## 2. Stockage

Table `reglages(nom TEXT PRIMARY KEY, valeur TEXT NOT NULL, modifie_le TEXT NOT NULL)`, migration 11
de `services/database.py`. `valeur` est un littéral JSON. **Ligne absente = défaut de `.env`.**
`.env` n'est jamais réécrit ; le retour au défaut est un `DELETE` de la ligne.

Au démarrage (`lifespan`, après `init_db`), `charger()` lit la table dans un cache mémoire. Une
ligne d'un nom inconnu, ou dont la valeur n'est plus dans les bornes, est ignorée et journalisée :
le défaut protège. Le backend est un seul processus (ADR-008) : le cache s'écrit avec la base et
n'a pas besoin d'invalidation.

## 3. Une seule lecture, et le moment où elle vaut

```python
# backend/src/tessera/reglages.py  (signatures, pas d'implémentation)
@dataclass(frozen=True)
class Reglage:
    nom: str; type: Literal["float", "int", "bool"]
    minimum: float | None; maximum: float | None
    libelle: str; effet: Literal["prochain_run", "machine"]

REGISTRE: Mapping[str, Reglage]

@dataclass(frozen=True)
class ReglagesEffectifs:
    run_max_budget_usd: float; llm_max_budget_usd: float; dialogue_timeout_s: float
    max_parallel_test_runs: int; keep_awake_during_runs: bool

class ReglageInvalide(ValueError): ...

def valider(nom: str, valeur: object) -> float | int | bool: ...   # bornes, type, ni bool pour float, ni NaN
async def charger(db_path: Path) -> None: ...
async def ecrire(db_path: Path, nom: str, valeur: object) -> ReglagesEffectifs: ...
async def retirer(db_path: Path, nom: str) -> ReglagesEffectifs: ...
def du_moment() -> ReglagesEffectifs: ...    # défaut `.env` (relu de `settings` à chaque appel) + surcharges
def figer(valeurs: ReglagesEffectifs | None = None) -> ReglagesEffectifs: ...   # pose un ContextVar
def courants() -> ReglagesEffectifs: ...     # le snapshot du run s'il y en a un, sinon du_moment()
```

`du_moment()` relit `settings.<nom>` à chaque appel (et non à l'import) : les tests qui posent
`settings.run_max_budget_usd` en `monkeypatch` continuent de marcher.

**Plafonds et délai** (`run_max_budget_usd`, `llm_max_budget_usd`, `dialogue_timeout_s`) : lus par
`courants()`. `RunRegistry.ouvrir` range `du_moment()` dans `RunActif.reglages` ; le handler de
`POST /orchestrator/run` appelle `figer(run.reglages)` juste après, avant de construire
l'orchestrateur : la tâche du run, créée ensuite, hérite du `ContextVar`. Hors d'un run (chat, routes),
`courants()` rend la valeur du moment. Un agent ne peut donc pas relever le plafond de son propre run.

**Machine** (`max_parallel_test_runs`, `keep_awake_during_runs`) : lus par `du_moment()`, car ils ne
décrivent pas un run mais la machine, et un snapshot par run ferait osciller un sémaphore partagé.
Deux conséquences à corriger dans le code existant :

- `test_runner._get_semaphore` crée un `asyncio.Semaphore(limit)` une fois : un changement n'y serait
  jamais lu. Il devient un limiteur dont la limite se relit à chaque acquisition ; ceux qui tiennent
  déjà un créneau le gardent.
- `eveil.retenir()` et `eveil.relacher()` lisent tous deux le réglage : coupé entre les deux, la
  machine ne se rendrait jamais. `relacher` ne consulte plus rien ; relâcher est toujours sûr.

Tous les sites de lecture passent par ce module : `assemblage_run.py`, `routers/orchestrator.py`
(`/limits`), `run_executor.py` (`dialogue_du_run`), `providers/par_role.py`, `test_runner.py`, `eveil.py`.
Un test interdit `settings.<nom modifiable>` ailleurs que dans `reglages.py` et `config.py`.

## 4. Sécurité

Trois menaces : une page servie en local par une app qu'un agent a écrite ; un agent qui a `Bash`
et appelle l'API avec `curl` ; un humain qui se trompe d'un zéro.

1. **`Origin` obligatoire et déclaré sur toute écriture de `/api/v1/reglages`** (PUT, DELETE), vérifié
   dans `HostOriginMiddleware` avec `_declared_origins()` (5173-5176, Tauri, `ALLOWED_ORIGINS` —
   ticket-754), pas avec le contrôle « loopback sur tout port » des autres routes. Un `Origin` absent est
   refusé ici, alors qu'il passe ailleurs : un navigateur en envoie toujours un sur un PUT, curl non.
   Réponse 403. `STATIC_TOKEN`, s'il est posé, reste exigé par-dessus.
2. **Bornes dures** (§1) : même un appel autorisé ne pose pas `0` ni un plafond hors tableau.
3. **Le garde de `Bash`** refuse les commandes d'accès réseau (`curl`, `wget`, `Invoke-WebRequest`,
   `Invoke-RestMethod`, `python -c`) qui nomment `/api/v1/reglages`. Lexical : il attrape une erreur ;
   forger un `Origin` à la main reste une évasion, que seule la limite ci-dessous borne.

Limite assumée : un agent déterminé peut, avec un `Origin` forgé, relever un plafond **dans les
bornes** pour les runs suivants. Il ne peut ni toucher le sien, ni dépasser le maximum du registre, ni
poser « sans plafond ». Chaque écriture est journalisée (`reglage_modifie` : nom, ancienne et nouvelle
valeur — rien de secret) et relisible dans le fil de logs.

## 5. Contrat d'API (`routers/reglages.py`, préfixe `/api/v1`)

- `GET /reglages` → liste de `{nom, libelle, type, valeur, defaut, minimum, maximum, modifie, effet,
  runs_ouverts}`. `valeur` est celle du prochain run ; `defaut` celle de `.env` ; `runs_ouverts` le nombre
  de runs qui gardent encore l'ancienne valeur (`RunRegistry`).
- `PUT /reglages/{nom}` corps `{"valeur": …}` → l'élément mis à jour. 404 nom inconnu, 422 hors bornes
  ou mauvais type, 403 `Origin`.
- `DELETE /reglages/{nom}` → l'élément revenu au défaut.
- `GET /orchestrator/limits` existe déjà (ticket-197) : il rend `courants()`.

## 6. Interface

Un bouton « Réglages » au pied du rail, sous la cloche, hors du `tablist` : le même ressort que `Cloche`
(popover, `useFermetureAuDehors`), pas une destination. Icône d'engrenage neuve, `IconEngrenage` : le
`IconSettings` existant (un disque et huit rayons) se lit comme un soleil, c'est ce qu'écarte le ticket.
Chaque ligne : libellé, champ, défaut de `.env`, « Appliquer », « Revenir au défaut » si `modifie`, et
l'effet dit en clair (« au prochain run », « dès la prochaine suite de tests »). Si `runs_ouverts > 0`, la
ligne dit combien de runs gardent l'ancienne valeur. Couleurs : ADR-026, le violet en fond seulement.

## 7. Ce que ça ne tranche pas

- Les **bornes numériques** du §1 : une proposition, c'est une décision de budget.
- Si `chat_max_conversation_usd` rejoint le registre.
- Une confirmation avant de relever un plafond : écartée ici, l'`Origin` et les bornes suffisent ;
  à rouvrir si un relèvement accidentel se produit.

## 8. Découpage

805 module `reglages` et table ; 806 snapshot par run et plafonds ; 807 réglages de machine et
lecture unique ; 808 route et garde d'`Origin` ; 809 garde de `Bash` ; 810 bouton et panneau.
