"""Analyse du remote d'un dépôt et noms de forge — ticket-699.

Des fonctions pures : elles lisent une chaîne et rendent un nom d'hébergeur ou
un `owner/repo`. Elles n'ont aucun lien avec l'ouverture ni le merge d'une PR,
et `project_loader` les importe sans passer par le workflow GitHub.
"""


#: Les hébergeurs reconnus, pour nommer celui qu'on a devant soi.
_FORGES = {
    "github.com": "GitHub",
    "dev.azure.com": "Azure DevOps",
    "bitbucket.org": None,  # nommé par son hôte, faute de mieux
}


def _forge_depuis_hote(host: str) -> str | None:
    """The readable name of a forge from its lowercased hostname."""
    host = host.lower()
    for cle, nom in _FORGES.items():
        if host == cle or host.endswith("." + cle):
            return nom or host
    if "gitlab" in host:
        return "GitLab"
    return host or None


def parse_remote(raw: str | None) -> tuple[str | None, str | None]:
    """Parse any remote form into (forge_name, 'owner/repo').

    Accepted forms:
    - 'owner/repo'                              → GitHub assumed
    - 'https://github.com/owner/repo'
    - 'https://github.com/owner/repo.git'
    - 'git@github.com:owner/repo.git'

    Returns (None, None) when the input is empty or unrecognisable.
    The raw value in agents.json is never rewritten (ADR-036 pattern).
    """
    if not raw:
        return None, None

    raw = raw.strip()

    # SSH form: git@host:owner/repo[.git]
    if raw.startswith("git@") and ":" in raw:
        after_at = raw[4:]  # drop 'git@'
        host, _, path = after_at.partition(":")
        slug = path.removesuffix(".git")
        return _forge_depuis_hote(host), slug

    # HTTPS form: https://[user@]host/owner/repo[.git]
    if "://" in raw:
        sans_schema = raw.split("://", 1)[1]
        host_part, sep, rest = sans_schema.partition("/")
        if not sep:
            return None, None
        host = host_part.split("@")[-1]
        slug = rest.removesuffix(".git")
        return _forge_depuis_hote(host), slug

    # Short form: owner/repo (no scheme, no host → GitHub assumed)
    if "/" in raw:
        return "GitHub", raw

    return None, None


def nom_de_la_forge(remote: str | None) -> str | None:
    """Le nom lisible de l'hébergeur d'un dépôt, ou son hôte à défaut.

    Dire « ce dépôt n'est pas sur GitHub » sans dire où il est n'aide personne
    à décider quoi faire.
    """
    if not remote:
        return None
    # Deux formes coexistent : `https://[identifiant@]hote/chemin` et
    # `git@hote:chemin`. Retirer le schéma d'abord, sinon « https » passe pour
    # l'hôte.
    sans_schema = remote.split("://", 1)[-1]
    hote = sans_schema.split("/")[0].split("@")[-1].split(":")[0].lower()
    return _forge_depuis_hote(hote)


def forge_supportee(remote: str | None) -> bool:
    """True si l'IDE sait ouvrir une pull request sur ce dépôt.

    Seul GitHub l'est : `GitHubService` tape sur `api.github.com`. Ailleurs, le
    bouton poussait la branche **puis** échouait sur l'appel d'API — donc il
    poussait sans rien demander. Sur le dépôt d'un client, pousser est
    précisément la décision qui ne se prend pas par mégarde (ticket-081).
    """
    return nom_de_la_forge(remote) == "GitHub"
