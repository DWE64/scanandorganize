"""
Extraction des métadonnées depuis le texte du document (regex, heuristiques).
- type_document (facture / avoir / inconnu)
- date (FR + ISO)
- montant TTC
- numéro facture
- fournisseur (best effort : raison sociale, SIRET, etc.)
"""
import re
from datetime import date
from typing import Optional

from basic_scanner.models import ExtractedData

# --- Patterns ---

# Dates FR : 31/12/2024, 31-12-2024, 31.12.2024
DATE_FR = re.compile(
    r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b"
)
# ISO : 2024-12-31
DATE_ISO = re.compile(
    r"\b(20\d{2})[/\-](\d{2})[/\-](\d{2})\b"
)
# Mois en lettres FR : 31 décembre 2024
MONTHS_FR = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
)
DATE_FR_LONG = re.compile(
    r"\b(\d{1,2})\s+(" + "|".join(MONTHS_FR) + r")\s+(\d{4})\b",
    re.IGNORECASE
)

# Montant TTC : 1 234,56 €, 1234.56 EUR, Total TTC 1234.56, etc.
MONTANT_TTC = re.compile(
    r"(?:total\s+ttc|ttc\s*:?|montant\s+ttc|total\s+à\s+payer)\s*:?\s*"
    r"([\d\s]+[,\.]\d{2})\s*(?:€|eur|euros?)?",
    re.IGNORECASE
)
# Fallback : dernier montant avec décimales et €
MONTANT_FALLBACK = re.compile(
    r"([\d\s]+[,\.]\d{2})\s*(?:€|eur|euros?)\b",
    re.IGNORECASE
)

# Numéro facture
NUM_FACTURE = re.compile(
    r"(?:facture\s*n[°ºo]?\s*:?|invoice\s*(?:no|n°|#)?\s*:?|n°\s*facture\s*:?)\s*"
    r"([A-Z0-9\-/]+)",
    re.IGNORECASE
)
NUM_FACTURE_ALT = re.compile(
    r"(?:n°|no\.?|#)\s*([A-Z0-9\-/]{4,})",
    re.IGNORECASE
)

# Mots-clés type document (ordre de test : avoir avant facture, puis devis, courrier, plan, impots)
KEYWORDS_FACTURE = ("facture", "invoice", "rechnung")
KEYWORDS_AVOIR = ("avoir", "credit note", "crédit", "remboursement", "refund")
KEYWORDS_DEVIS = ("devis", "quote", "estimation", "proposition commerciale", "proposal")
KEYWORDS_COURRIER = ("courrier", "lettre", "letter", "mail", "correspondance")
KEYWORDS_PLAN = ("plan", "schéma", "schema", "drawing", "plan de", "plan d'")
KEYWORDS_IMPOTS = ("impôts", "impots", "avis d'imposition", "avis d'impôt", "dgfip", "urssaf", "caf", "taxe", "fiscal", "revenus")


def _parse_fr_date(m: re.Match) -> Optional[date]:
    d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    try:
        return date(y, mth, d)
    except ValueError:
        return None


def _parse_iso_date(m: re.Match) -> Optional[date]:
    y, mth, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mth, d)
    except ValueError:
        return None


def _parse_fr_long_date(m: re.Match) -> Optional[date]:
    day = int(m.group(1))
    month_name = m.group(2).lower()
    year = int(m.group(3))
    try:
        month = MONTHS_FR.index(month_name) + 1
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def extract_date(texte: str) -> Optional[date]:
    """Extrait la première date plausible (facture) du texte."""
    for pattern, parse in [
        (DATE_ISO, _parse_iso_date),
        (DATE_FR, _parse_fr_date),
        (DATE_FR_LONG, _parse_fr_long_date),
    ]:
        for m in pattern.finditer(texte):
            d = parse(m)
            if d and (date(2000, 1, 1) <= d <= date(2030, 12, 31)):
                return d
    return None


def extract_montant_ttc(texte: str) -> Optional[float]:
    """Extrait le montant TTC (heuristique + regex)."""
    m = MONTANT_TTC.search(texte)
    if m:
        s = m.group(1).replace(" ", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            pass
    for m in reversed(list(MONTANT_FALLBACK.finditer(texte))):
        s = m.group(1).replace(" ", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            continue
    return None


def extract_numero_facture(texte: str) -> Optional[str]:
    """Extrait le numéro de facture."""
    m = NUM_FACTURE.search(texte)
    if m:
        return m.group(1).strip()
    m = NUM_FACTURE_ALT.search(texte)
    if m:
        return m.group(1).strip()
    return None


def extract_type_document(texte: str) -> str:
    """Détermine le type : facture_fournisseur, avoir, devis, courrier, plan, impots, inconnu."""
    lower = texte.lower()
    for k in KEYWORDS_AVOIR:
        if k in lower:
            return "avoir"
    for k in KEYWORDS_FACTURE:
        if k in lower:
            return "facture_fournisseur"
    for k in KEYWORDS_DEVIS:
        if k in lower:
            return "devis"
    for k in KEYWORDS_COURRIER:
        if k in lower:
            return "courrier"
    for k in KEYWORDS_PLAN:
        if k in lower:
            return "plan"
    for k in KEYWORDS_IMPOTS:
        if k in lower:
            return "impots"
    return "inconnu"


def extract_fournisseur_raw(texte: str) -> Optional[str]:
    """
    Best effort : extrait une raison sociale ou identifiant (ligne après "Facture", SIRET, etc.).
    Retourne le texte brut à faire matcher plus tard avec le dictionnaire.
    """
    # Ligne après "Facture" ou en-tête
    m = re.search(
        r"(?:facture|invoice)\s*(?:n°?)?\s*[^\n]*\n\s*([^\n]{3,80})",
        texte,
        re.IGNORECASE,
    )
    if m:
        line = m.group(1).strip()
        # Enlever numéros seuls
        if re.match(r"^[\d\s\-]+$", line):
            return None
        return line[:80]

    # SIRET présent : on peut retourner une ligne contenant un nom
    siret = re.search(r"SIRET\s*:?\s*[\d\s]{14,}", texte, re.IGNORECASE)
    if siret:
        start = max(0, siret.start() - 80)
        chunk = texte[start : siret.start()]
        lines = [l.strip() for l in chunk.splitlines() if len(l.strip()) > 4]
        if lines:
            return lines[-1][:80]

    # Première ligne non vide significative (souvent le fournisseur)
    for line in texte.splitlines():
        line = line.strip()
        if 5 <= len(line) <= 80 and not re.match(r"^[\d\s\.,€]+$", line):
            return line
    return None


def extract_all(texte: str) -> ExtractedData:
    """
    Lance toutes les extractions et retourne un ExtractedData.
    Le champ fournisseur et confidence seront complétés par classify + suppliers.
    """
    type_doc = extract_type_document(texte)
    date_doc = extract_date(texte)
    montant = extract_montant_ttc(texte)
    numero = extract_numero_facture(texte)
    fournisseur_raw = extract_fournisseur_raw(texte)

    return ExtractedData(
        type_document=type_doc,
        date_doc=date_doc,
        montant_ttc=montant,
        numero_facture=numero,
        fournisseur=None,
        fournisseur_raw=fournisseur_raw,
        texte_complet=texte,
        confidence=0.0,
    )
