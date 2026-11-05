# Les secrets de Tessera dans le coffre du système — conception

ADR-073, ticket-772. Aucun code n'est écrit ici : ce document fixe les interfaces
et les cas limites, les tickets 794 à 799 les implémentent.

## Ce que le coffre apporte, et ce qu'il n'apporte pas

Apporte : plus de fichier en clair à lire, copier, sauvegarder, synchroniser ou
trouver par un `Grep` ; un chiffrement au repos lié à la session de l'utilisateur
(Gestionnaire d'identification sous Windows, Trousseau sous macOS, Secret Service
ou KWallet sous Linux) ; un secret qui ne suit plus un clone, un worktree ou une
archive du dépôt.

N'apporte pas : une frontière entre processus. Tout programme lancé par
l'utilisateur lit le coffre de l'utilisateur. Un agent qui obtient un shell peut
exécuter `keyring`. Le plafond d'un jeton reste sa portée et son expiration
(ADR-053) ; le garde de lecture reste un contrôle lexical qui attrape une erreur.

Source : documentation de `keyring` (https://keyring.readthedocs.io/en/latest/),
qui ne donne aucune analyse de sécurité du backend Windows et ne nomme pas
l'exception d'un coffre absent : le détecteur ci-dessous s'appuie sur le type du
backend rendu par `keyring.get_keyring()`, et un test le vérifie.

## 1. Ce qui passe au coffre

Entrée du coffre : service `tessera`, nom d'utilisateur = nom de la variable en
majuscules.

| Dans le coffre (9) | Reste dans `.env` |
| --- | --- |
| `ANTHROPIC_API_KEY`, `GITHUB_TOKEN` | `VERCEL_TEAM_ID`, `NEON_ORG_ID`, `GITHUB_REPO`, `GITHUB_BASE_BRANCH` |
| `VERCEL_TOKEN`, `NEON_API_KEY`, `RESEND_API_KEY`, `STRIPE_API_KEY`, `CLOUDFLARE_API_TOKEN` | `LLM_*`, `OLLAMA_*`, plafonds, délais, chemins, `ALLOWED_*`, `LLM_PROVIDER` |
| `STATIC_TOKEN`, `FORBIDDEN_TERMS` | `SECRETS_SOURCE` (nouveau, non secret) |

`FORBIDDEN_TERMS` n'est pas un jeton, mais la liste dit des noms de clients : elle
se range comme un secret, et gagne au passage de valoir dans tous les worktrees
(le hook lisait `.env` relatif au dossier courant, absent d'un worktree).

Hors liste, inchangé : la clé d'un rôle `openai_compatible` (`api_key_env`,
ticket-669) se lit dans l'environnement du processus, pas dans `Settings`.

## 2. Interfaces

```python
# backend/src/tessera/coffre.py
SERVICE: Final = "tessera"
NOMS_SECRETS: Final[tuple[str, ...]]   # les neuf noms, en majuscules

class CoffreAbsent(Exception): ...     # aucun trousseau utilisable sur cette machine
class CoffreEnErreur(Exception): ...   # il existe, l'appel a échoué (verrouillé, refusé)

class Coffre(Protocol):
    def lire(self, nom: str) -> str | None: ...        # None : entrée absente
    def ecrire(self, nom: str, valeur: str) -> None: ... # relit et compare, sinon CoffreEnErreur
    def supprimer(self, nom: str) -> None: ...         # entrée absente : sans effet
    def presents(self) -> frozenset[str]: ...          # parmi NOMS_SECRETS

def coffre_du_systeme() -> Coffre:
    """Raise CoffreAbsent for keyring's fail and null backends."""
```

Le backend `null` de `keyring` rend toujours « absent » et jette les écritures : il
compte comme `CoffreAbsent`, sinon une migration croirait avoir écrit. `ecrire`
relit toujours (la limite de taille d'une entrée Windows, à confirmer par le test,
ferait sinon tronquer ou refuser sans bruit) ; une valeur trop longue lève
`CoffreEnErreur`, jamais une troncature.

```python
# backend/src/tessera/config.py (ajouts)
secrets_source: Literal["coffre", "env"] = "coffre"

class SourceCoffre(PydanticBaseSettingsSource): ...
# settings_customise_sources : init, variables d'environnement, SourceCoffre,
# .env, valeurs par défaut.
```

`SECRETS_SOURCE` se lit avant le reste, dans la variable d'environnement puis dans
`.env` (`dotenv_values`, valeur non secrète) : il décide si `SourceCoffre` existe.

## 3. Lecture au démarrage et échec fermé

| Mode | Coffre | Entrée | Résultat |
| --- | --- | --- | --- |
| `coffre` | absent (`CoffreAbsent`) | — | refus : `ConfigurationError`, message sans valeur, qui dit de déclarer `SECRETS_SOURCE=env` |
| `coffre` | en erreur | — | refus : `ConfigurationError` (« déverrouille le coffre ») |
| `coffre` | disponible | présente | valeur du coffre |
| `coffre` | disponible | absente | repli sur `.env`, puis défaut vide ; chaque secret lu dans `.env` journalise `secret_en_clair_dans_env` (nom seul) |
| `env` | jamais lu | — | variables d'environnement, `.env`, défaut, sans avertissement |
| `auto` (défaut) | absent ou en erreur | — | `.env` et avertissement `coffre_indisponible_repli_env` ; **refus** si `.env` porte une ligne `# NOM : dans le coffre` |
| `auto` | disponible | présente / absente | comme `coffre` |

**Décision de Benjamin, 05/11 :** Tessera reste utilisable sur tous ses PC sans
rien configurer, d'où le défaut `auto`. Un PC migré (§4, étape 5) passe en
`coffre` ; un PC jamais migré démarre sur son `.env`. Le refus ci-dessous reste
entier pour tout secret migré.

Pourquoi refuser plutôt que se replier : un `STATIC_TOKEN` migré, sur une machine
sans coffre, rouvrirait l'API en silence ; une `FORBIDDEN_TERMS` introuvable
désarmerait la porte de push. Un secret *absent* n'est pas une erreur : il garde
le sens d'aujourd'hui (jeton vide : mise en ligne inactive, livraison refusée par
`manques_avant_depart`, `LLM_PROVIDER=anthropic_api` signalé par `doctor`).

Un secret présent dans le coffre et dans `.env` : le coffre gagne, l'avertissement
nomme le doublon.

Variable d'environnement explicite : elle prime sur tout, comme aujourd'hui (CI,
Docker, essai ponctuel). `SECRETS_SOURCE=env` est la seule façon de ne jamais
toucher le coffre : la suite de tests la pose (`backend/tests/conftest.py`).

## 4. Ce que le backend ne fait jamais d'un secret

- l'exporter dans `os.environ` (pydantic-settings ne le fait pas : ne pas
  l'ajouter) ou dans l'`env` d'un sous-processus ;
- l'afficher, le journaliser, le renvoyer par l'API ou `/health` ;
- le passer en argument de commande (visible dans la liste des processus) :
  l'écriture passe par l'entrée standard.

Masquage : `Settings.valeurs_des_jetons()` ne couvre aujourd'hui que cinq jetons ;
`GITHUB_TOKEN`, `STATIC_TOKEN` et `ANTHROPIC_API_KEY` n'étaient ni masqués dans les
logs ni traités comme termes interdits. Les huit secrets hors `FORBIDDEN_TERMS` se
déclarent à `SECRETS` ; `FORBIDDEN_TERMS` non, c'est déjà la liste que la porte
applique. `env_du_sous_processus` vide les variables homonymes en plus des six
actuelles : `STATIC_TOKEN`, `FORBIDDEN_TERMS`.

## 5. Migration (`python -m tessera.coffre_cli`, verbe `tessera.ps1 secrets`)

Sous-commandes : `migrer`, `set <NOM>` (valeur sur l'entrée standard ; le verbe
PowerShell la demande en `Read-Host -AsSecureString`), `supprimer <NOM>`,
`lister` (nom → `coffre`, `.env` ou `absent`, jamais une valeur), `termes`
(voir §6). Pas de sous-commande qui affiche un secret, `termes` exceptée.

`migrer`, pour chaque nom de `NOMS_SECRETS` lu dans `.env` :

1. valeur vide ou placeholder (`sk-ant-...`, `ghp_...`, tout ce qui finit par
   `...`) : ignorée ;
2. le coffre porte déjà une valeur différente : rien n'est écrasé, la ligne reste,
   le nom est rapporté en conflit (l'humain tranche avec `set`) ;
3. sinon `ecrire` (qui relit et compare) ; en cas d'échec la ligne reste ;
4. seulement après la relecture, la ligne devient
   `# NOM : dans le coffre (tessera.ps1 secrets)` ; les commentaires et les autres
   lignes sont conservés tels quels ;
5. `SECRETS_SOURCE=coffre` s'ajoute s'il manque.

Le nouveau `.env` s'écrit dans un fichier voisin puis `os.replace`. Aucun
secret n'est écrit en clair ailleurs : ni sauvegarde `.env.bak` (une copie en
clair), ni fichier temporaire contenant une valeur, ni sortie. Interrompue entre
l'écriture du coffre et celle de `.env`, la commande est rejouable : les deux
portent la valeur, la relance retire la ligne. Code de sortie non nul si une
relecture a échoué ou si un conflit reste.

Les valeurs ont existé en clair : la sortie rappelle de les faire tourner (jeton
régénéré) si le disque est sauvegardé ou synchronisé. Le coffre ne rattrape pas
ce passé.

## 6. FORBIDDEN_TERMS, hook `pre-push`, `scan_historique.py`

Un seul résolveur : `coffre_cli termes` applique l'ordre du §3 (variable
d'environnement, coffre, `.env`) et écrit la liste sur sa sortie standard.

- code 0, sortie vide : aucune liste déclarée, aucun contrôle en local (ADR-048,
  ADR-050 amendé du 2026-09-29 inchangé) ;
- code non nul : le contrôle n'a pas pu juger (coffre absent ou en erreur en mode
  `coffre`, `uv` introuvable, exception) : push refusé, message « lance
  `uv sync` ou déclare `SECRETS_SOURCE=env` ».

Le hook (stdlib seul) appelle `uv run --project <racine>/backend python -m
tessera.coffre_cli termes`, la racine se déduisant du chemin du hook ; il perd sa
lecture de `.env`. La CI ne change pas : `termes_interdits_ci.py` lit le secret
GitHub dans l'environnement, et `.github/workflows/` est hors de portée d'un
agent (ADR-067). `scan_historique.py` prend le même résolveur.

`termes` est la seule commande qui écrit une valeur de coffre ; sa sortie va au
hook, pas à un terminal.

## 7. Garde d'ADR-053 étendu

`garde_jetons.py` refuse en outre un `Bash` qui *exécute* le coffre : premier mot
d'un segment de commande ∈ {`cmdkey`, `vaultcmd`, `keyring`, `secret-tool`,
`security` suivi d'une sous-commande `*-generic-password` ou
`*-internet-password`}, `python -m keyring`, `-m tessera.coffre_cli`, ou un texte
de commande qui contient `import keyring`, `from keyring`, `Get-StoredCredential`,
`CredRead`, `PasswordVault`. Une recherche textuelle (`grep keyring`) passe :
refuser le mot seul interdirait de lire le code qui l'utilise. Plafond dit
dans le message de refus, comme pour `.env` : `__import__('key' + 'ring')` passe.

## 8. Choix rejetés

- **Chiffrer `.env`** (SOPS, DPAPI maison) : la clé ou le mot de passe se retrouve
  à côté, ou demande une saisie à chaque démarrage.
- **Un gestionnaire externe** (1Password CLI, Vault) : un compte, un binaire et un
  réseau de plus pour un outil local à un seul utilisateur.
- **Repli silencieux sur `.env`** quand le coffre manque : il rouvre l'API et
  désarme la porte de push sans que personne le voie (ADR-039).
- **Un secret éditable depuis l'interface** : ticket-780 les exclut déjà ; le
  coffre se tient par `tessera.ps1`.

## 9. Ce que ce design ne tranche pas

- Faut-il vider aussi `GITHUB_TOKEN` (et `GH_TOKEN`) dans l'`env` des agents ? Leurs
  lectures `gh` (ADR-067) peuvent en dépendre ; à mesurer avant de le décider.
- Rotation des jetons déjà passés en clair : une action de l'utilisateur.
- Typage des champs en `SecretStr` (aujourd'hui `str` pour `github_token`,
  `static_token`, `anthropic_api_key`) : le masquage par `SECRETS` suffit pour
  l'instant ; un changement mécanique d'une vingtaine d'appels, à part.
- Le comportement exact de `keyring` sur une machine sans trousseau Linux ni sur une
  machine à Smart App Control : les dépendances de `keyring` sous Windows sont du
  Python pur, à confirmer au premier `uv sync` du ticket-794.

## Tickets

794 module `coffre` · 795 lecture par `Settings` · 796 masquage et
sous-processus · 797 migration et verbe PowerShell · 798 hook `pre-push` et scan
d'historique · 799 garde de lecture · 800 doctor, `/health`, `.env.example`,
Docker.
