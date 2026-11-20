"""Prints the housekeeping report of the projects folder — ticket-913.

    python scripts/releve_menage.py [--projets a,b] [--age-jours 30] [--racine chemin]

Mesure seulement : n'écrit, n'archive ni ne supprime rien.
"""
import argparse
import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from tessera.services.projets.releve_menage import releve_menage  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--projets", default="")
    parseur.add_argument("--age-jours", type=int, default=30)
    parseur.add_argument("--racine", type=Path, default=Path(__file__).resolve().parent.parent / "projects")
    args = parseur.parse_args(argv)
    if not args.racine.is_dir():
        sys.stderr.write(f"dossier introuvable : {args.racine}\n")
        return 2
    noms = [n.strip() for n in args.projets.split(",") if n.strip()] or None
    sys.stdout.write(releve_menage(args.racine, args.age_jours, noms) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
