"""
Dictionnaire de fournisseurs + matching fuzzy (rapidfuzz).
Mappe le texte brut extrait vers un nom de dossier normalisé.
"""
from typing import Optional

from basic_scanner.logging_conf import get_logger
from basic_scanner.models import ExtractedData

logger = get_logger("suppliers")

# Seuil de similarité (0..100) pour accepter un match
DEFAULT_SCORE_CUTOFF = 70


def _get_rapidfuzz():
    try:
        from rapidfuzz import fuzz
        return fuzz
    except ImportError:
        return None


def resolve_fournisseur(
    extracted: ExtractedData,
    mapping_fournisseurs: dict[str, str],
    score_cutoff: int = DEFAULT_SCORE_CUTOFF,
) -> None:
    """
    Trouve le fournisseur normalisé à partir de fournisseur_raw et du mapping.
    Utilise rapidfuzz pour le fuzzy matching. Modifie extracted.fournisseur en place.
    """
    raw = extracted.fournisseur_raw
    if not raw or not mapping_fournisseurs:
        return

    fuzz_mod = _get_rapidfuzz()
    if not fuzz_mod:
        # Fallback : match exact dans le mapping
        for key, value in mapping_fournisseurs.items():
            if key.lower() in raw.lower():
                extracted.fournisseur = value
                return
        return

    # Liste des clés (alias / raisons sociales) et valeurs (nom dossier)
    candidates = list(mapping_fournisseurs.items())
    best_ratio = 0
    best_value: Optional[str] = None

    for alias, folder_name in candidates:
        # ratio sur la chaîne complète
        r = fuzz_mod.ratio(raw.lower(), alias.lower())
        if r >= score_cutoff and r > best_ratio:
            best_ratio = r
            best_value = folder_name
        # partial_ratio si le texte extrait contient l'alias
        pr = fuzz_mod.partial_ratio(raw.lower(), alias.lower())
        if pr >= score_cutoff and pr > best_ratio:
            best_ratio = pr
            best_value = folder_name

    if best_value:
        extracted.fournisseur = best_value
        logger.debug("Fournisseur matché: '%s' -> '%s' (score %s)", raw, best_value, best_ratio)
