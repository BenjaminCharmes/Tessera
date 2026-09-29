"""Les chemins qui portent la politique du run se refusent — ticket-119.

Le périmètre d'ADR-031 enferme l'agent **dans** son projet. Mais c'est dans le
projet que vivent les fichiers qui décident de ce que le run a le droit de
faire : `agents.json` (autonomie, racine git), `.git/hooks/` (du code que
`git commit` exécute dans le process de l'orchestrateur, avec l'identité de
l'utilisateur — sans une seule commande git dans `Bash`), `.git/config` (qui
peut désigner ces hooks ailleurs), `.claude/settings*.json` (des hooks que le
CLI exécute au run suivant) et `.github/workflows/` (ce qui rend la CI
« verte » en mode `merge`). S'y ajoutent les consignes que le CLI charge dans
les sessions suivantes : `CLAUDE.md`, et les skills, commandes et agents de
`.claude/` (ticket-240).

Le refus est distinct de celui du hors-périmètre : ces fichiers **sont** dans
le projet. Dire à l'agent qu'il est ailleurs l'enverrait chercher un autre
endroit où écrire la même chose. Le message dit ce qui est protégé, et
pourquoi — un projet dont un dossier s'appelle `.github/workflows` par usage
réel doit comprendre le refus, pas le contourner.
"""
from fnmatch import fnmatch
from pathlib import Path

#: Ce que l'agent lit quand on lui refuse un chemin protégé.
PROTECTION_REFUS = (
    "Écriture refusée : ce fichier porte les règles qui bornent ce run, et un "
    "run ne modifie pas ses propres règles. {motif}. Si le changement est "
    "vraiment nécessaire, décris-le dans ton rapport : c'est une décision qui "
    "revient à l'utilisateur, entre deux runs."
)

#: Le manifeste du projet : autonomie, racine git, mode des artefacts.
_MANIFESTE = "agents.json"
#: Le motif de fichier de réglages du CLI, sous `.claude/`.
_REGLAGES_CLI = "settings*.json"
#: Les consignes que le CLI charge dans chaque session (ticket-240).
_CONSIGNES = {"CLAUDE.md", "CLAUDE.local.md"}
#: Les dossiers de `.claude/` dont le CLI charge le contenu à la demande.
_DOSSIERS_CLI = {"skills", "commands", "agents"}


def motif_de_protection(chemin: str, project_path: Path, racine: Path) -> str | None:
    """Pourquoi `chemin` est protégé, ou None s'il ne l'est pas.

    `racine` est celle sous laquelle l'agent a le droit d'écrire — le projet,
    ou le dépôt qui le contient s'il l'a déclaré (ADR-028) ; les chemins
    relatifs s'y résolvent. Le `.git/` et le `.github/` d'un projet
    `ancestor` sont à la racine du dépôt, pas du projet : on regarde donc
    tous les segments, pas seulement le premier.
    """
    try:
        cible = Path(chemin)
        if not cible.is_absolute():
            cible = racine / cible
        cible = cible.resolve()
    except (OSError, ValueError):
        return None

    if cible == (project_path / _MANIFESTE).resolve():
        return "`agents.json` déclare l'autonomie, la racine git et les artefacts du projet"

    # Un `CLAUDE.md` réécrit pendant un run devient la consigne de tous les
    # agents suivants, sans ticket pour l'autoriser (règle 5 de CLAUDE.md).
    if cible.name in _CONSIGNES:
        return (
            f"`{cible.name}` est chargé dans chaque session du CLI : le réécrire "
            "change la consigne de tous les agents suivants"
        )

    segments = cible.parts
    if ".git" in segments:
        return (
            "`.git/` est le dépôt lui-même : un hook ou une configuration "
            "déposés là s'exécuteraient au commit, sous l'identité de l'utilisateur"
        )
    for precedent, suivant in zip(segments, segments[1:]):
        if precedent == ".claude" and fnmatch(suivant, _REGLAGES_CLI):
            return (
                "`.claude/settings*.json` déclare des hooks que le CLI exécuterait "
                "au run suivant"
            )
        if precedent == ".claude" and suivant in _DOSSIERS_CLI:
            return (
                f"`.claude/{suivant}/` porte des consignes que le CLI charge à la "
                "demande dans les sessions suivantes"
            )
        if precedent == ".github" and suivant == "workflows":
            return (
                "`.github/workflows/` est la CI dont le verdict autorise le merge "
                "(ADR-029)"
            )
    return None


def refus_de_protection(motif: str) -> str:
    """Le message complet, motif inclus."""
    return PROTECTION_REFUS.format(motif=motif)
