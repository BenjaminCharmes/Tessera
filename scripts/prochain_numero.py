"""Prints the next free ticket or ADR number — ticket-659.

    python scripts/prochain_numero.py ticket
    python scripts/prochain_numero.py adr [--base develop] [--projet chemin]

Lit l'arbre du projet, `origin/<base>` et les branches `origin/ticket-*` : un
numéro qui n'existe que sur une autre branche compte. Lancé depuis le dossier
du projet, ou avec `--projet`. Sans remote lisible, seul l'arbre répond.

Le numéro rendu est réservé (ticket-848) dans `numeros_reserves.json`, sous
`IDE_STATE_DIR` : il n'est plus jamais rendu, utilisé ou non. `--sans-reserver`
lit seulement et n'écrit rien.
"""
import argparse
import os
import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from tessera.services.noyau.numerotation import BASE_PAR_DEFAUT, prochain_numero, reserver  # noqa: E402


def dossier_etat() -> Path:
    """`IDE_STATE_DIR`, else the state folder of the settings."""
    voulu = os.environ.get("IDE_STATE_DIR")
    if voulu:
        return Path(voulu)
    from tessera.config import settings  # import tardif : tire pydantic

    return settings.ide_state_dir


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("genre", choices=("ticket", "adr"))
    parseur.add_argument("--base", default=BASE_PAR_DEFAUT)
    parseur.add_argument("--projet", type=Path, default=Path.cwd())
    parseur.add_argument("--sans-reserver", action="store_true")
    args = parseur.parse_args(argv)
    if args.sans_reserver:
        numero = prochain_numero(args.projet, args.genre, args.base)
    else:
        numero = reserver(args.projet, args.genre, args.base, dossier_etat())
    sys.stdout.write(f"{numero}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
