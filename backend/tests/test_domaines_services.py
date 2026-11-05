"""Ratchet on the services domains (ADR-076, ticket-826).

A module of `services/` imports its own domain or a lower one, never a higher
one. The domain of a module is its folder (`services/<domaine>/...`) or, for a
module still flat, its line in `A_DEPLACER` (`scripts/domaines_services.py`).
"""

import ast
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from tests.test_sens_des_imports import _cibles_import_from, _paquet_du_module

SOURCES = Path(__file__).resolve().parent.parent / "src" / "tessera"
_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from domaines_services import A_DEPLACER, ORDRE  # noqa: E402

# Paquets de premier niveau de `tessera/` admis par ADR-076.
PAQUETS_AUTORISES: frozenset[str] = frozenset({"models", "services", "routers", "utils"})
# Paquets encore tolérés hors des couches : aucun depuis le ticket-816, et le
# test refuse une tolérance devenue sans objet.
PAQUETS_TOLERES: frozenset[str] = frozenset()

# Écarts mesurés à l'ouverture du ticket-826, après reclassement, au format
# "chemin relatif à src/tessera -> domaine importé". Cliquet : un écart corrigé
# se retire d'ici, aucun ne s'ajoute (reclasser le module vaut mieux). Aucun ne
# tombe par un seul déplacement de module.
ECARTS_DOMAINES: frozenset[str] = frozenset({
    # Le verrou et le registre des runs tirent file_vivante (pipeline).
    "services/agents/chat_suggestion.py -> pipeline",
    "services/ci_watcher.py -> pipeline",
    # Les noms et la déclaration des providers vivent dans providers/.
    "services/manifeste_ecriture.py -> providers",
    "services/project_loader.py -> providers",
    # L'orchestrateur aiguille vers le mode file, qui l'importe en retour.
    "services/orchestrator.py -> file",
    # Le type `Livraison` porté par l'événement de fin de run.
    "services/pipeline_events.py -> livraison",
})


def domaine_du_module(relatif: Path, table: Mapping[str, str]) -> str | None:
    """Return the domain of a module path relative to src/tessera, if any."""
    parties = relatif.parts
    if len(parties) < 2 or parties[0] != "services":
        return None
    if len(parties) > 2:
        return parties[1]
    return table.get(Path(parties[1]).stem)


def _domaine_cible(cible: list[str], ordre: Sequence[str], table: Mapping[str, str]) -> str | None:
    """Return the domain an import target (without 'tessera') belongs to."""
    if len(cible) < 2 or cible[0] != "services":
        return None
    if cible[1] in table:
        return table[cible[1]]
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
                # `from tessera.services import x` vise le module `services.x`.
                if cible == ["services"] and noms != ["services"]:
                    cibles.extend(["services", nom] for nom in noms)
                else:
                    cibles.append(cible)
    return cibles


def mesurer_domaines(racine: Path, ordre: Sequence[str], table: Mapping[str, str]) -> set[str]:
    """List every import towards a higher domain as 'path -> domain'."""
    rang = {domaine: i for i, domaine in enumerate(ordre)}
    ecarts: set[str] = set()
    for fichier in sorted((racine / "services").rglob("*.py")):
        if "__pycache__" in fichier.parts:
            continue
        relatif = fichier.relative_to(racine)
        source = domaine_du_module(relatif, table)
        if source not in rang:
            continue
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        for cible in _cibles(arbre, _paquet_du_module(fichier, racine)):
            domaine = _domaine_cible(cible, ordre, table)
            if domaine in rang and rang[domaine] > rang[source]:
                ecarts.add(f"{relatif.as_posix()} -> {domaine}")
    return ecarts


def couverture(racine: Path, ordre: Sequence[str], table: Mapping[str, str]) -> list[str]:
    """Check that every flat module has a domain and every table line a file."""
    plats = {f.stem for f in (racine / "services").glob("*.py")} - {"__init__"}
    messages = [
        f"services/{nom}.py : module à plat sans domaine. Range-le dans services/<domaine>/ "
        "ou ajoute sa ligne à A_DEPLACER (scripts/domaines_services.py)."
        for nom in sorted(plats - set(table))
    ]
    messages += [
        f"{nom} : ligne de A_DEPLACER sans fichier services/{nom}.py. Retire-la."
        for nom in sorted(set(table) - plats)
    ]
    messages += [
        f"{nom} : domaine inconnu « {domaine} » dans A_DEPLACER."
        for nom, domaine in sorted(table.items()) if domaine not in ordre
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
    table: Mapping[str, str],
    connus: frozenset[str],
    toleres: frozenset[str] = frozenset(),
) -> list[str]:
    """Run every domain check and compare the gaps with the listed ones, both ways."""
    mesures = mesurer_domaines(racine, ordre, table)
    messages = couverture(racine, ordre, table) + paquets(racine, toleres)
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


def test_real_tree_follows_the_domains() -> None:
    assert controler(SOURCES, ORDRE, A_DEPLACER, ECARTS_DOMAINES, PAQUETS_TOLERES) == []


def test_import_to_a_lower_domain_passes(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/h.py", "from tessera.services.b import f\n")
    _ecrire(tmp_path, "services/b.py")
    assert controler(tmp_path, _ORDRE, {"h": "haut", "b": "bas"}, frozenset()) == []


def test_import_to_a_higher_domain_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/b.py", "import tessera.services.h\n")
    _ecrire(tmp_path, "services/h.py")
    messages = controler(tmp_path, _ORDRE, {"h": "haut", "b": "bas"}, frozenset())
    assert messages == ["services/b.py -> haut : import vers un domaine de rang plus haut (ADR-076)."]


def test_flat_module_domain_comes_from_the_table() -> None:
    assert domaine_du_module(Path("services/x.py"), {"x": "milieu"}) == "milieu"
    assert domaine_du_module(Path("routers/x.py"), {"x": "milieu"}) is None


def test_package_domain_comes_from_its_folder(tmp_path: Path) -> None:
    assert domaine_du_module(Path("services/bas/x.py"), {"x": "haut"}) == "bas"
    _ecrire(tmp_path, "services/bas/x.py", "from tessera.services.haut.y import f\n")
    _ecrire(tmp_path, "services/haut/y.py", "from tessera.services.bas import x\n")
    assert mesurer_domaines(tmp_path, _ORDRE, {}) == {"services/bas/x.py -> haut"}


def test_from_services_import_module_is_resolved(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/b.py", "from tessera.services import m, h as alias\n")
    table = {"b": "bas", "m": "milieu", "h": "haut"}
    assert mesurer_domaines(tmp_path, _ORDRE, table) == {
        "services/b.py -> milieu", "services/b.py -> haut",
    }


def test_type_checking_and_lazy_imports_count(tmp_path: Path) -> None:
    _ecrire(
        tmp_path,
        "services/b.py",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    from tessera.services.h import T\n"
        "def f() -> None:\n    from tessera.services.m import g\n",
    )
    table = {"b": "bas", "m": "milieu", "h": "haut"}
    assert mesurer_domaines(tmp_path, _ORDRE, table) == {
        "services/b.py -> milieu", "services/b.py -> haut",
    }


def test_undeclared_flat_module_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/nouveau.py")
    _ecrire(tmp_path, "services/__init__.py")
    messages = controler(tmp_path, _ORDRE, {}, frozenset())
    assert len(messages) == 1
    assert "services/nouveau.py : module à plat sans domaine" in messages[0]


def test_table_entry_without_file_fails(tmp_path: Path) -> None:
    (tmp_path / "services").mkdir()
    messages = controler(tmp_path, _ORDRE, {"parti": "bas"}, frozenset())
    assert messages == ["parti : ligne de A_DEPLACER sans fichier services/parti.py. Retire-la."]


def test_unknown_top_level_package_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/__init__.py")
    _ecrire(tmp_path, "divers/__init__.py")
    _ecrire(tmp_path, "config.py")
    messages = controler(tmp_path, _ORDRE, {}, frozenset())
    assert messages == ["tessera/divers/ : paquet de premier niveau hors models, services, routers, utils."]


def test_tolerated_package_passes(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/__init__.py")
    _ecrire(tmp_path, "agents/github_sync.py")
    assert controler(tmp_path, _ORDRE, {}, frozenset(), frozenset({"agents"})) == []
    (tmp_path / "agents" / "github_sync.py").unlink()
    (tmp_path / "agents").rmdir()
    messages = controler(tmp_path, _ORDRE, {}, frozenset(), frozenset({"agents"}))
    assert messages == ["tessera/agents/ : toléré mais absent. Retire-le de PAQUETS_TOLERES."]


def test_listed_gap_passes_while_it_exists(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/b.py", "from tessera.services.h import f\n")
    _ecrire(tmp_path, "services/h.py")
    table = {"b": "bas", "h": "haut"}
    assert controler(tmp_path, _ORDRE, table, frozenset({"services/b.py -> haut"})) == []


def test_listed_gap_already_fixed_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/b.py", "x = 1\n")
    messages = controler(tmp_path, _ORDRE, {"b": "bas"}, frozenset({"services/b.py -> haut"}))
    assert messages == [
        "services/b.py -> haut : écart corrigé mais toujours listé. Retire l'entrée de ECARTS_DOMAINES."
    ]
