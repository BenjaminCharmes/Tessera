"""Name the failing test files on the testeur's journal line (ticket-1006)."""
from tessera.services.verification.relance_instable import lire_les_echecs
from tessera.services.verification.resultat_de_test import TestResult

MAX_FICHIERS = 5


def fichiers_en_echec(result: TestResult) -> list[str]:
    """Return the failing test files, each once, in the order they were read."""
    sortie = "\n".join([result.failure_details, result.output_summary])
    vus: list[str] = []
    for echec in lire_les_echecs(sortie):
        if echec.fichier not in vus:
            vus.append(echec.fichier)
    return vus


def ligne_du_testeur(result: TestResult) -> str:
    """The journal line: the summary, then the failing files when tests are red."""
    if result.passed:
        return result.output_summary
    fichiers = fichiers_en_echec(result)
    if not fichiers:
        return result.output_summary
    nommes = ", ".join(fichiers[:MAX_FICHIERS])
    reste = len(fichiers) - MAX_FICHIERS
    suffixe = f" +{reste}" if reste > 0 else ""
    return f"{result.output_summary} — fichiers en échec : {nommes}{suffixe}"
