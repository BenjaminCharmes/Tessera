"""Ratchet on the services domains (ADR-076, tickets 826 and 825).

A module of `services/` lives in its domain folder (`services/<domaine>/...`)
and imports its own domain or a lower one, never a higher one. No module sits
flat under `services/`, and every folder of `services/` is a domain of ORDRE.
"""

import ast
from collections.abc import Sequence
from pathlib import Path

from tests.test_sens_des_imports import _cibles_import_from, _paquet_du_module

SOURCES = Path(__file__).resolve().parent.parent / "src" / "tessera"

# Les dix-huit domaines, du rang le plus bas au plus haut : un module n'importe
# que son domaine ou un domaine de rang plus bas (ADR-076).
ORDRE: tuple[str, ...] = (
    "noyau",
    "projets",
    "usage",
    "provisioning",
    "gardes",
    "git_workspace",
    "worktrees",
    "github",
    "providers",
    "verification",
    "verdicts",
    "agents",
    "documentation",
    "creation_projet",
    "livraison",
    "pipeline",
    "file",
    "supervision",
)

# Paquets de premier niveau de `tessera/` admis par ADR-076.
PAQUETS_AUTORISES: frozenset[str] = frozenset({"models", "services", "routers", "utils"})
# Paquets encore tolérés hors des couches : aucun depuis le ticket-816, et le
# test refuse une tolérance devenue sans objet.
PAQUETS_TOLERES: frozenset[str] = frozenset()

# Écarts mesurés à l'ouverture du ticket-826, après reclassement, au format
# "chemin relatif à src/tessera -> domaine importé". Cliquet : un écart corrigé
# se retire d'ici, aucun ne s'ajoute (reclasser le module vaut mieux).
ECARTS_DOMAINES: frozenset[str] = frozenset({
    # Le verrou et le registre des runs tirent file_vivante (pipeline).
    "services/agents/chat_suggestion.py -> pipeline",
    "services/livraison/ci_watcher.py -> pipeline",
    # Les noms et la déclaration des providers vivent dans providers/.
    "services/projets/manifeste_ecriture.py -> providers",
    "services/projets/project_loader.py -> providers",
    # L'orchestrateur aiguille vers le mode file, qui l'importe en retour.
    "services/pipeline/orchestrator.py -> file",
    # Le type `Livraison` porté par l'événement de fin de run.
    "services/noyau/pipeline_events.py -> livraison",
})


def domaine_du_module(relatif: Path) -> str | None:
    """Return the domain folder of a module path relative to src/tessera, if any."""
    parties = relatif.parts
    if len(parties) < 3 or parties[0] != "services":
        return None
    return parties[1]


def _domaine_cible(cible: list[str], ordre: Sequence[str]) -> str | None:
    """Return the domain an import target (without 'tessera') belongs to."""
    if len(cible) < 2 or cible[0] != "services":
        return None
    return cible[1] if cible[1] in ordre else None


def _cibles(arbre: ast.AST, paquet: list[str]) -> list[list[str]]:
    """Return every tessera import target of a module, lazy and TYPE_CHECKING ones included."""
    cibles: list[list[str]] = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            for alias in noeud.names:
                parties = alias.name.split(".")
                if parties[0] == "tessera":
                    cibles.append(parties[1:])
        elif isinstance(noeud, ast.ImportFrom):
            noms = [alias.name for alias in noeud.names]
            for cible in _cibles_import_from(noeud, paquet):
                # `from tessera.services import x` vise le domaine `services.x`.
                if cible == ["services"] and noms != ["services"]:
                    cibles.extend(["services", nom] for nom in noms)
                else:
                    cibles.append(cible)
    return cibles


def mesurer_domaines(racine: Path, ordre: Sequence[str]) -> set[str]:
    """List every import towards a higher domain as 'path -> domain'."""
    rang = {domaine: i for i, domaine in enumerate(ordre)}
    ecarts: set[str] = set()
    for fichier in sorted((racine / "services").rglob("*.py")):
        if "__pycache__" in fichier.parts:
            continue
        relatif = fichier.relative_to(racine)
        source = domaine_du_module(relatif)
        if source not in rang:
            continue
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        for cible in _cibles(arbre, _paquet_du_module(fichier, racine)):
            domaine = _domaine_cible(cible, ordre)
            if domaine in rang and rang[domaine] > rang[source]:
                ecarts.add(f"{relatif.as_posix()} -> {domaine}")
    return ecarts


def couverture(racine: Path, ordre: Sequence[str]) -> list[str]:
    """Check that no file sits flat in services/ and that folders and ORDRE match."""
    services = racine / "services"
    plats = sorted(f.name for f in services.iterdir() if f.is_file() and f.name != "__init__.py")
    dossiers = {d.name for d in services.iterdir() if d.is_dir() and d.name != "__pycache__"}
    messages = [
        f"services/{nom} : fichier à plat. Range-le dans services/<domaine>/ (ADR-076)."
        for nom in plats
    ]
    messages += [
        f"services/{nom}/ : dossier hors des domaines d'ORDRE (ADR-076)."
        for nom in sorted(dossiers - set(ordre))
    ]
    messages += [
        f"{nom} : domaine d'ORDRE sans dossier services/{nom}/."
        for nom in ordre if nom not in dossiers
    ]
    return messages


def paquets(racine: Path, toleres: frozenset[str]) -> list[str]:
    """Check the top-level packages of tessera/ against the allowed ones."""
    presents = {
        d.name for d in racine.iterdir() if d.is_dir() and d.name != "__pycache__"
    }
    messages = [
        f"tessera/{nom}/ : paquet de premier niveau hors models, services, routers, utils."
        for nom in sorted(presents - PAQUETS_AUTORISES - toleres)
    ]
    messages += [
        f"tessera/{nom}/ : toléré mais absent. Retire-le de PAQUETS_TOLERES."
        for nom in sorted(toleres - presents)
    ]
    return messages


def controler(
    racine: Path,
    ordre: Sequence[str],
    connus: frozenset[str],
    toleres: frozenset[str] = frozenset(),
) -> list[str]:
    """Run every domain check and compare the gaps with the listed ones, both ways."""
    mesures = mesurer_domaines(racine, ordre)
    messages = couverture(racine, ordre) + paquets(racine, toleres)
    messages += [
        f"{e} : import vers un domaine de rang plus haut (ADR-076)." for e in sorted(mesures - connus)
    ]
    messages += [
        f"{e} : écart corrigé mais toujours listé. Retire l'entrée de ECARTS_DOMAINES."
        for e in sorted(connus - mesures)
    ]
    return messages


_ORDRE = ("bas", "milieu", "haut")


def _ecrire(racine: Path, chemin: str, source: str = "") -> None:
    cible = racine / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(source, encoding="utf-8")


def _arbre(racine: Path) -> None:
    """Write an empty services/ with one folder per test domain."""
    _ecrire(racine, "services/__init__.py")
    for domaine in _ORDRE:
        _ecrire(racine, f"services/{domaine}/__init__.py")


def test_real_tree_follows_the_domains() -> None:
    assert controler(SOURCES, ORDRE, ECARTS_DOMAINES, PAQUETS_TOLERES) == []


def test_order_holds_the_eighteen_domains_of_adr_076() -> None:
    assert len(ORDRE) == 18
    assert ORDRE[0] == "noyau"
    assert ORDRE[-1] == "supervision"
    assert len(set(ORDRE)) == len(ORDRE)


def test_import_to_a_lower_domain_passes(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "services/haut/h.py", "from tessera.services.bas.b import f\n")
    _ecrire(tmp_path, "services/bas/b.py")
    assert controler(tmp_path, _ORDRE, frozenset()) == []


def test_import_to_a_higher_domain_fails(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "services/bas/b.py", "import tessera.services.haut.h\n")
    _ecrire(tmp_path, "services/haut/h.py")
    messages = controler(tmp_path, _ORDRE, frozenset())
    assert messages == [
        "services/bas/b.py -> haut : import vers un domaine de rang plus haut (ADR-076)."
    ]


def test_domain_comes_from_the_folder() -> None:
    assert domaine_du_module(Path("services/bas/x.py")) == "bas"
    assert domaine_du_module(Path("services/x.py")) is None
    assert domaine_du_module(Path("routers/x.py")) is None


def test_from_services_import_domain_is_resolved(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/bas/b.py", "from tessera.services import milieu, haut as alias\n")
    assert mesurer_domaines(tmp_path, _ORDRE) == {
        "services/bas/b.py -> milieu", "services/bas/b.py -> haut",
    }


def test_type_checking_and_lazy_imports_count(tmp_path: Path) -> None:
    _ecrire(
        tmp_path,
        "services/bas/b.py",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    from tessera.services.haut.h import T\n"
        "def f() -> None:\n    from tessera.services.milieu.m import g\n",
    )
    assert mesurer_domaines(tmp_path, _ORDRE) == {
        "services/bas/b.py -> milieu", "services/bas/b.py -> haut",
    }


def test_flat_file_in_services_fails(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "services/nouveau.py")
    messages = controler(tmp_path, _ORDRE, frozenset())
    assert messages == [
        "services/nouveau.py : fichier à plat. Range-le dans services/<domaine>/ (ADR-076)."
    ]


def test_folder_outside_the_order_fails(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "services/divers/x.py")
    messages = controler(tmp_path, _ORDRE, frozenset())
    assert messages == ["services/divers/ : dossier hors des domaines d'ORDRE (ADR-076)."]


def test_domain_without_folder_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/__init__.py")
    _ecrire(tmp_path, "services/bas/__init__.py")
    _ecrire(tmp_path, "services/haut/__init__.py")
    messages = controler(tmp_path, _ORDRE, frozenset())
    assert messages == ["milieu : domaine d'ORDRE sans dossier services/milieu/."]


def test_unknown_top_level_package_fails(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "divers/__init__.py")
    _ecrire(tmp_path, "config.py")
    messages = controler(tmp_path, _ORDRE, frozenset())
    assert messages == ["tessera/divers/ : paquet de premier niveau hors models, services, routers, utils."]


def test_tolerated_package_passes(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "agents/github_sync.py")
    assert controler(tmp_path, _ORDRE, frozenset(), frozenset({"agents"})) == []
    (tmp_path / "agents" / "github_sync.py").unlink()
    (tmp_path / "agents").rmdir()
    messages = controler(tmp_path, _ORDRE, frozenset(), frozenset({"agents"}))
    assert messages == ["tessera/agents/ : toléré mais absent. Retire-le de PAQUETS_TOLERES."]


def test_listed_gap_passes_while_it_exists(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "services/bas/b.py", "from tessera.services.haut.h import f\n")
    _ecrire(tmp_path, "services/haut/h.py")
    assert controler(tmp_path, _ORDRE, frozenset({"services/bas/b.py -> haut"})) == []


def test_listed_gap_already_fixed_fails(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "services/bas/b.py", "x = 1\n")
    messages = controler(tmp_path, _ORDRE, frozenset({"services/bas/b.py -> haut"}))
    assert messages == [
        "services/bas/b.py -> haut : écart corrigé mais toujours listé. Retire l'entrée de ECARTS_DOMAINES."
    ]
