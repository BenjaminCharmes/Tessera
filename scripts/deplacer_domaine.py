"""Move one services domain into its folder and rewrite its references (ticket-827).

    python scripts/deplacer_domaine.py <domaine> [--dry-run]

Reads `scripts/domaines_services.py` (ticket-826), renames every flat module
of the domain into `services/<domaine>/`, removes their lines from
`A_DEPLACER`, and rewrites the references in `backend/src`, `backend/tests`,
`scripts/` and `Makefile`: imports, `python -m`, string literals (`patch`,
`importlib`) and file paths. Nothing is written when an old path would be left
behind; after writing, the tree is read again to prove none is.

Reported, never fixed: `__file__` or `parents[N]` in a moved module, a bare
`"x.py"` elsewhere in the code, and old paths in `docs/` and `projects/`.
No git command is run: git recognises the renames by content similarity.
"""
import argparse
import ast
import difflib
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from deplacer_domaine_texte import (
    MOTIF_EMPLACEMENT,
    lignes_a_relire,
    motif_nom_de_fichier,
    motif_texte,
    reecrire,
    references_mortes,
)

RACINE_PAR_DEFAUT = Path(__file__).resolve().parents[1]
SERVICES = Path("backend/src/tessera/services")
TABLE = Path("scripts/domaines_services.py")
DOSSIERS_CODE = ("backend/src", "backend/tests", "scripts")
FICHIERS_CODE = ("Makefile",)
DOSSIERS_TEXTE = ("docs", "projects")
_IGNORES = frozenset({
    "__pycache__", "node_modules", ".venv", ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache",
})
_SUFFIXES_CODE = frozenset({".py", ".ps1", ".mjs", ".js", ".sh", ".toml", ""})
_SUFFIXES_TEXTE = frozenset({".md", ".txt", ".py", ".json", ".yml", ".yaml", ".toml", ".ps1"})


class ErreurDeDomaine(Exception):
    """The domain is unknown, already empty, or its files are not where expected."""


@dataclass
class Plan:
    """What moving a domain changes, computed without writing anything."""

    domaine: str
    deplacements: list[tuple[Path, Path]]
    creer_init: bool
    modifications: dict[Path, tuple[str, str]] = field(default_factory=dict)
    signalements: list[str] = field(default_factory=list)
    mortes: list[str] = field(default_factory=list)


def _lire(chemin: Path) -> str:
    # Lu et écrit en octets : les fins de ligne du fichier restent les siennes.
    return chemin.read_bytes().decode("utf-8")


def _ecrire(chemin: Path, texte: str) -> None:
    chemin.write_bytes(texte.encode("utf-8"))


def lire_table(racine: Path) -> tuple[tuple[str, ...], dict[str, str]]:
    """Read ORDRE and A_DEPLACER from the table, without importing it."""
    valeurs: dict[str, object] = {}
    for noeud in ast.parse(_lire(racine / TABLE)).body:
        if isinstance(noeud, ast.AnnAssign) and isinstance(noeud.target, ast.Name) and noeud.value:
            valeurs[noeud.target.id] = ast.literal_eval(noeud.value)
        elif isinstance(noeud, ast.Assign) and isinstance(noeud.targets[0], ast.Name):
            valeurs[noeud.targets[0].id] = ast.literal_eval(noeud.value)
    ordre, table = valeurs.get("ORDRE"), valeurs.get("A_DEPLACER")
    if not isinstance(ordre, tuple) or not isinstance(table, dict):
        raise ErreurDeDomaine(f"{TABLE} : ORDRE ou A_DEPLACER illisible")
    return tuple(str(d) for d in ordre), {str(k): str(v) for k, v in table.items()}


def retirer_du_tableau(texte: str, domaine: str) -> str:
    """Remove the domain's lines (and its comment header) from the table text."""
    ligne = re.compile(rf"""^\s*(["']\w+["']\s*:\s*["']{re.escape(domaine)}["'],|# {re.escape(domaine)})\s*$""")
    return "".join(l for l in texte.splitlines(keepends=True) if not ligne.match(l))


def _parcourir(racine: Path, dossiers: tuple[str, ...], suffixes: frozenset[str]) -> list[Path]:
    fichiers: list[Path] = []
    for dossier in dossiers:
        base = racine / dossier
        if not base.is_dir():
            continue
        fichiers += [
            f for f in base.rglob("*")
            if f.is_file() and f.suffix in suffixes
            and not _IGNORES.intersection(f.relative_to(racine).parts)
        ]
    return sorted(fichiers)


def fichiers_de_code(racine: Path) -> list[Path]:
    """Every file whose references the script rewrites."""
    fichiers = _parcourir(racine, DOSSIERS_CODE, _SUFFIXES_CODE)
    fichiers += [racine / f for f in FICHIERS_CODE if (racine / f).is_file()]
    return [f for f in fichiers if f != racine / TABLE]


def fichiers_de_texte(racine: Path) -> list[Path]:
    """Files under docs/ and projects/, tracked by git when the root is a repository."""
    if (racine / ".git").exists():
        sortie = subprocess.run(
            ["git", "-C", str(racine), "ls-files", "-z", "--", *DOSSIERS_TEXTE],
            capture_output=True, check=True,
        ).stdout.decode("utf-8")
        return [racine / p for p in sortie.split("\0") if p and Path(p).suffix in _SUFFIXES_TEXTE]
    return _parcourir(racine, DOSSIERS_TEXTE, _SUFFIXES_TEXTE)


def _relatif(racine: Path, chemin: Path) -> str:
    return chemin.relative_to(racine).as_posix()


def _modules_par_dossier(racine: Path, domaine: str, modules: list[str]) -> dict[str, set[str]]:
    dossier = racine / SERVICES / domaine
    presents = {f.stem for f in dossier.glob("*.py")} | {d.name for d in dossier.glob("*/")}
    return {domaine: presents | set(modules)}


def planifier(racine: Path, domaine: str) -> Plan:
    """Compute the moves, the rewrites, the reports and the old paths left behind."""
    ordre, table = lire_table(racine)
    if domaine not in ordre:
        raise ErreurDeDomaine(f"domaine inconnu : {domaine} (connus : {', '.join(ordre)})")
    modules = sorted(m for m, d in table.items() if d == domaine)
    if not modules:
        raise ErreurDeDomaine(f"{domaine} : aucun module à plat à déplacer, le domaine est vide")
    services, dossier = racine / SERVICES, racine / SERVICES / domaine
    absents = [m for m in modules if not (services / f"{m}.py").is_file()]
    occupes = [m for m in modules if (dossier / f"{m}.py").exists()]
    if absents or occupes:
        raise ErreurDeDomaine(
            f"{domaine} : modules absents {absents}, déjà présents dans le dossier {occupes}"
        )
    plan = Plan(
        domaine=domaine,
        deplacements=[(services / f"{m}.py", dossier / f"{m}.py") for m in modules],
        creer_init=not (dossier / "__init__.py").exists(),
    )
    deplaces = {m: domaine for m in modules}
    destinations = dict(plan.deplacements)
    par_dossier = _modules_par_dossier(racine, domaine, modules)
    motif_fichier = motif_nom_de_fichier(deplaces)
    for fichier in fichiers_de_code(racine):
        ancien = _lire(fichier)
        nouveau = reecrire(ancien, deplaces, python=fichier.suffix == ".py")
        if nouveau != ancien:
            plan.modifications[fichier] = (ancien, nouveau)
        affiche = _relatif(racine, destinations.get(fichier, fichier))
        plan.mortes += [f"{affiche}:{e}" for e in references_mortes(nouveau, deplaces, par_dossier)]
        motifs = [motif_fichier] + ([MOTIF_EMPLACEMENT] if fichier in destinations else [])
        for motif in motifs:
            plan.signalements += [f"{affiche}:{n}: {l}" for n, l in lignes_a_relire(nouveau, motif)]
    for fichier in fichiers_de_texte(racine):
        try:
            texte = _lire(fichier)
        except (OSError, UnicodeDecodeError) as erreur:
            # Du texte seulement signalé : un fichier illisible ne bloque rien.
            plan.signalements.append(f"{_relatif(racine, fichier)}: illisible ({type(erreur).__name__})")
            continue
        plan.signalements += [
            f"{_relatif(racine, fichier)}:{n}: {l}"
            for n, l in lignes_a_relire(texte, motif_texte(deplaces))
        ]
    return plan


def appliquer(racine: Path, plan: Plan) -> list[str]:
    """Write the plan, then read the tree again: return any old path still present."""
    for fichier, (_, nouveau) in plan.modifications.items():
        _ecrire(fichier, nouveau)
    dossier = racine / SERVICES / plan.domaine
    dossier.mkdir(exist_ok=True)
    if plan.creer_init:
        _ecrire(dossier / "__init__.py", "")
    for source, cible in plan.deplacements:
        source.rename(cible)
    _ecrire(racine / TABLE, retirer_du_tableau(_lire(racine / TABLE), plan.domaine))
    restes = [f"{_relatif(racine, s)} : toujours là" for s, _ in plan.deplacements if s.exists()]
    _, table = lire_table(racine)
    restes += [f"{TABLE.as_posix()} : {m} toujours listé" for m, d in table.items() if d == plan.domaine]
    deplaces = {s.stem: plan.domaine for s, _ in plan.deplacements}
    par_dossier = _modules_par_dossier(racine, plan.domaine, list(deplaces))
    for fichier in fichiers_de_code(racine):
        restes += [
            f"{_relatif(racine, fichier)}:{e}"
            for e in references_mortes(_lire(fichier), deplaces, par_dossier)
        ]
    return restes


def _diff(racine: Path, fichier: Path, ancien: str, nouveau: str) -> list[str]:
    avant, apres = ancien.splitlines(), nouveau.splitlines()
    sortie: list[str] = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=avant, b=apres).get_opcodes():
        if op == "equal":
            continue
        sortie.append(f"  {_relatif(racine, fichier)}:{i1 + 1}")
        sortie += [f"    - {l.strip()}" for l in avant[i1:i2]]
        sortie += [f"    + {l.strip()}" for l in apres[j1:j2]]
    return sortie


def afficher(racine: Path, plan: Plan, a_blanc: bool) -> None:
    """Print the plan: moves, line changes, reports, old paths left behind."""
    titre = "à blanc, rien n'est écrit" if a_blanc else "écriture"
    print(f"Domaine {plan.domaine} : {len(plan.deplacements)} modules ({titre})")
    print("Déplacements :")
    for source, cible in plan.deplacements:
        print(f"  {_relatif(racine, source)} -> {_relatif(racine, cible)}")
    if plan.creer_init:
        print(f"  + {_relatif(racine, racine / SERVICES / plan.domaine / '__init__.py')} (vide)")
    print(f"Références réécrites : {len(plan.modifications)} fichiers")
    for fichier, (ancien, nouveau) in plan.modifications.items():
        for ligne in _diff(racine, fichier, ancien, nouveau):
            print(ligne)
    print(f"À relire à la main : {len(plan.signalements)}")
    for signalement in plan.signalements:
        print(f"  {signalement}")
    if plan.mortes:
        print(f"Anciens chemins qui resteraient : {len(plan.mortes)}")
        for morte in plan.mortes:
            print(f"  {morte}")


def main(argv: list[str] | None = None) -> int:
    """Entry point: 0 when done (or planned), 1 when an old path remains, 2 on a bad domain."""
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    analyseur.add_argument("domaine")
    analyseur.add_argument("--dry-run", action="store_true", help="liste sans rien écrire")
    analyseur.add_argument("--racine", type=Path, default=RACINE_PAR_DEFAUT)
    options = analyseur.parse_args(argv)
    racine = options.racine.resolve()
    try:
        plan = planifier(racine, options.domaine)
    except ErreurDeDomaine as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 2
    afficher(racine, plan, options.dry_run)
    if plan.mortes:
        print("Rien n'est écrit : des anciens chemins resteraient.", file=sys.stderr)
        return 1
    if options.dry_run:
        return 0
    restes = appliquer(racine, plan)
    for reste in restes:
        print(f"  reste : {reste}", file=sys.stderr)
    return 1 if restes else 0


if __name__ == "__main__":
    sys.exit(main())
