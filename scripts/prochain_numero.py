"""Prints the next free ticket or ADR number — ticket-659.

    python scripts/prochain_numero.py ticket
    python scripts/prochain_numero.py adr [--base develop] [--projet chemin]

Lit l'arbre du projet, `origin/<base>` et les branches `origin/ticket-*` : un
numéro qui n'existe que sur une autre branche compte. Lancé depuis le dossier
du projet, ou avec `--projet`. Sans remote lisible, seul l'arbre répond.
"""
import argparse
import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from tessera.services.numerotation import BASE_PAR_DEFAUT, prochain_numero  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("genre", choices=("ticket", "adr"))
    parseur.add_argument("--base", default=BASE_PAR_DEFAUT)
    parseur.add_argument("--projet", type=Path, default=Path.cwd())
    args = parseur.parse_args(argv)
    sys.stdout.write(f"{prochain_numero(args.projet, args.genre, args.base)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
