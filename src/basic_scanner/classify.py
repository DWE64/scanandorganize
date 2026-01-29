"""
Calcul du type de document et du score de confiance (0..1).
Confiance basée sur : fournisseur trouvé, date trouvée, type trouvé.
"""
from basic_scanner.models import ExtractedData


def compute_confidence(extracted: ExtractedData) -> float:
    """
    Calcule un score de confiance entre 0 et 1.
    Critères : fournisseur identifié, date présente, type document, numéro facture, montant.
    """
    score = 0.0
    # Fournisseur normalisé trouvé : poids fort
    if extracted.fournisseur:
        score += 0.35
    elif extracted.fournisseur_raw:
        score += 0.1  # Texte brut mais pas dans le mapping
    # Date
    if extracted.date_doc:
        score += 0.25
    # Type document reconnu
    if extracted.type_document in ("facture_fournisseur", "avoir", "devis", "courrier", "plan", "impots"):
        score += 0.2
    # Numéro facture
    if extracted.numero_facture:
        score += 0.1
    # Montant TTC
    if extracted.montant_ttc is not None:
        score += 0.1

    return min(1.0, round(score, 2))


def ensure_type_doc(extracted: ExtractedData) -> None:
    """
    Ajuste le type_document pour le chemin (slug) : FACT, AVR, DEVIS, COURRIER, PLAN, INCONNU.
    Modifie extracted en place.
    """
    slug_map = {
        "facture_fournisseur": "FACT",
        "avoir": "AVR",
        "devis": "DEVIS",
        "courrier": "COURRIER",
        "plan": "PLAN",
        "impots": "IMPOTS",
    }
    setattr(extracted, "_type_doc_slug", slug_map.get(extracted.type_document, "INCONNU"))


def get_type_doc_slug(extracted: ExtractedData) -> str:
    """Retourne le libellé court pour le nom de fichier (FACT, AVR, INCONNU)."""
    if hasattr(extracted, "_type_doc_slug"):
        return getattr(extracted, "_type_doc_slug")
    ensure_type_doc(extracted)
    return getattr(extracted, "_type_doc_slug")
