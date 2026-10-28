"""Probe: does `ResultMessage.usage` add up the turns of the tool loop? (ticket-605)

One short call makes the model read two files, so the loop has at least three
turns. The probe prints the `usage` of every assistant turn next to the one of
the final result, and `cumule_les_tours` reads the answer off those figures.
"""
from __future__ import annotations

import asyncio
import sys
from collections.abc import Mapping
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

_CLES_ENTREE = (
    "input_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)
_TOLERANCE = 0.02


def entree_totale(usage: Mapping[str, object]) -> int:
    """Input side of one `usage` dict: fresh + cache read + cache creation."""
    total = 0
    for cle in _CLES_ENTREE:
        valeur = usage.get(cle, 0)
        total += valeur if isinstance(valeur, int) else 0
    return total


def cumule_les_tours(par_tour: list[int], final: int) -> bool | None:
    """True if ``final`` is the sum of the turns, False if it is one turn only.

    ``None`` when neither reading fits (or there is under two turns, which
    cannot tell the two apart).
    """
    if len(par_tour) < 2 or final <= 0:
        return None
    if abs(final - sum(par_tour)) <= _TOLERANCE * final:
        return True
    if any(abs(final - tour) <= _TOLERANCE * final for tour in par_tour):
        return False
    return None


def ligne_de_sortie(par_tour: list[int], final: int) -> str:
    """The line the spec quotes: per-turn figures, final figure, conclusion."""
    verdict = cumule_les_tours(par_tour, final)
    lecture = {True: "cumule les tours", False: "ne rend qu'un tour", None: "indéterminé"}
    return (
        f"tours={par_tour} somme={sum(par_tour)} result.usage={final} "
        f"-> {lecture[verdict]}"
    )


async def _collecter(dossier: Path, fichiers: list[Path]) -> tuple[list[int], int]:
    consigne = (
        "Lis ces deux fichiers avec l'outil Read, un par un, puis réponds par "
        "un mot : " + ", ".join(str(f) for f in fichiers)
    )
    options = ClaudeAgentOptions(allowed_tools=["Read"], max_turns=6, cwd=str(dossier))
    vus: dict[str, int] = {}
    final = 0
    async for message in query(prompt=consigne, options=options):
        if isinstance(message, AssistantMessage) and message.usage:
            # Un message à plusieurs blocs se répète : une ligne par message_id.
            cle = message.message_id or f"sans-id-{len(vus)}"
            vus[cle] = entree_totale(message.usage)
        elif isinstance(message, ResultMessage) and message.usage:
            final = entree_totale(message.usage)
    return list(vus.values()), final


def main(argv: list[str]) -> int:
    """Run the probe on two files given as arguments; return an exit code."""
    if len(argv) != 2:
        sys.stderr.write("usage: sonde_usage.py <fichier_a> <fichier_b>\n")
        return 2
    fichiers = [Path(argv[0]).resolve(), Path(argv[1]).resolve()]
    par_tour, final = asyncio.run(_collecter(fichiers[0].parent, fichiers))
    sys.stdout.write(ligne_de_sortie(par_tour, final) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
