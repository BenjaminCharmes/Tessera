"""Moves the old months of the pipeline log into monthly archives — ticket-912.

    python scripts/archiver_journal.py [--projet id|chemin] [--garder-mois 2]

Les lignes des mois plus anciens que les `--garder-mois` derniers (mois courant
compris) partent dans `memory/journal/pipeline-log-AAAA-MM.md`. Rien n'est
supprimé ni commité. À lancer hors de toute file : le verrou d'un run vit dans
la mémoire du backend, ce script ne peut pas le lire.
"""
import argparse
import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from prochain_numero import resoudre_projet  # noqa: E402
from tessera.services.git_workspace.archive_journal import archiver_journal  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--projet", type=Path, default=Path.cwd())
    parseur.add_argument("--garder-mois", type=int, default=2)
    args = parseur.parse_args(argv)
    if args.garder_mois < 1:
        sys.stderr.write("--garder-mois doit valoir au moins 1\n")
        return 2
    projet = resoudre_projet(args.projet)
    if projet is None or not (projet / "memory").is_dir():
        sys.stderr.write(f"projet introuvable ou sans memory/ : {args.projet}\n")
        return 2
    deplaces = archiver_journal(projet, args.garder_mois)
    for mois, nombre in deplaces.items():
        sys.stdout.write(f"{mois} : {nombre} lignes\n")
    if not deplaces:
        sys.stdout.write("rien à archiver\n")
    sys.stdout.write("hors de toute file : aucun run ne doit écrire le journal\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
