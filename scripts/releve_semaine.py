"""Prints what each project shipped over a period — ticket-910.

    python scripts/releve_semaine.py --du 2026-11-03 --au 2026-11-09 [--exclure a,b] [--racine chemin]

Lit les fichiers des projets, sans LLM ni GitHub, et n'écrit rien.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

_RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RACINE / "backend" / "src"))

from tessera.services.projets.releve_semaine import releve_semaine  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Weekly report of shipped work per project.")
    parser.add_argument("--du", type=date.fromisoformat, required=True)
    parser.add_argument("--au", type=date.fromisoformat, required=True)
    parser.add_argument("--exclure", default="")
    parser.add_argument("--racine", type=Path, default=_RACINE / "projects")
    args = parser.parse_args(argv)
    exclure = [nom.strip() for nom in args.exclure.split(",") if nom.strip()]
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stdout.write(releve_semaine(args.racine, args.du, args.au, exclure))
    return 0


if __name__ == "__main__":
    sys.exit(main())
