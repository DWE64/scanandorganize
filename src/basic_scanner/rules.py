"""
Règles de classement : format chemin/nom, slugify.
Support des placeholders : fournisseur, YYYY, MM, DD, numero, montant, type_doc.
"""
import re
import unicodedata
from pathlib import Path
from typing import Any

from basic_scanner.classify import get_type_doc_slug
from basic_scanner.models import ExtractedData


def slugify(value: str, max_length: int = 80) -> str:
    """
    Nettoie une chaîne pour usage dans noms de dossiers/fichiers :
    accents normalisés, caractères spéciaux remplacés par _, pas d'espaces multiples.
    """
    if not value:
        return ""
    # Normalisation NFD et suppression des accents
    nfd = unicodedata.normalize("NFD", value)
    ascii_str = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Garder alphanum, espaces, tirets, underscores
    ascii_str = re.sub(r"[^\w\s\-]", " ", ascii_str)
    ascii_str = re.sub(r"[-\s]+", "_", ascii_str).strip("_")
    return ascii_str[:max_length] if max_length else ascii_str


def _format_montant(montant: float | None) -> str:
    if montant is None:
        return "0"
    return f"{montant:.2f}".replace(".", ",").replace(",", "_")  # éviter . dans nom fichier


def build_placeholders(extracted: ExtractedData, config: dict | None = None) -> dict[str, Any]:
    """
    Construit le dictionnaire des placeholders pour chemin et nom fichier.
    Les clés personnalisées (config['cles_personnalisees']) sont fusionnées après les clés intégrées.
    """
    d = extracted.date_doc
    yyyy = d.strftime("%Y") if d else "0000"
    mm = d.strftime("%m") if d else "00"
    dd = d.strftime("%d") if d else "00"
    fournisseur = (extracted.fournisseur or "Inconnu").strip()
    fournisseur_slug = slugify(fournisseur, 60)
    numero = (extracted.numero_facture or "N").strip()
    numero_slug = slugify(numero, 40)
    montant_str = _format_montant(extracted.montant_ttc)
    type_doc = get_type_doc_slug(extracted)
    impots_slug = fournisseur_slug if type_doc == "IMPOTS" else slugify("impots", 60)
    client_slug = fournisseur_slug

    out = {
        "fournisseur": fournisseur_slug,
        "client": client_slug,
        "impots": impots_slug,
        "YYYY": yyyy,
        "MM": mm,
        "DD": dd,
        "numero": numero_slug,
        "montant": montant_str,
        "type_doc": type_doc,
    }
    # Clés personnalisées (ajoutées/modifiables dans l'interface)
    if config:
        for item in config.get("cles_personnalisees") or []:
            if isinstance(item, dict):
                cle = (item.get("cle") or "").strip()
                val = (item.get("valeur_par_defaut") or "").strip()
                if cle:
                    out[cle] = val or cle
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                cle = str(item[0]).strip()
                val = str(item[1]).strip() if len(item) > 1 else ""
                if cle:
                    out[cle] = val or cle
    return out


def apply_template(template: str, placeholders: dict[str, Any]) -> str:
    """Remplace {key} par la valeur dans template."""
    result = template
    for key, value in placeholders.items():
        result = result.replace("{" + key + "}", str(value))
    # Nettoyer les placeholders non remplacés (optionnel)
    result = re.sub(r"\{[^}]+\}", "", result)
    return result.strip("/").strip("\\").strip()


def build_destination_path(
    racine_destination: str | Path,
    modele_chemin: str,
    extracted: ExtractedData,
    config: dict | None = None,
) -> Path:
    """
    Construit le chemin de destination (dossier) à partir du modèle et des données extraites.
    Supporte chemins UNC (\\\\NAS\\...).
    """
    root = Path(racine_destination)
    placeholders = build_placeholders(extracted, config)
    path_part = apply_template(modele_chemin, placeholders)
    # Éviter double backslash sur Windows sauf UNC
    parts = [p for p in path_part.replace("\\", "/").split("/") if p]
    return root.joinpath(*parts)


def build_destination_filename(
    modele_nom_fichier: str, extracted: ExtractedData, config: dict | None = None
) -> str:
    """Construit le nom de fichier de destination."""
    placeholders = build_placeholders(extracted, config)
    name = apply_template(modele_nom_fichier, placeholders)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def get_rule_for_type(type_document: str, config: dict) -> tuple[str, str] | None:
    """
    Retourne (modele_chemin, modele_nom_fichier) pour le type de document.
    Si config a regles_classement, utilise la règle dont le type correspond, sinon "défaut".
    Sinon retourne None (utiliser modele_chemin et modele_nom_fichier par défaut).
    """
    regles = config.get("regles_classement") or []
    if not regles:
        return None
    # Chercher une règle dont le type correspond
    for r in regles:
        t = (r.get("type") or "").strip().lower()
        if t == type_document.lower():
            return (r.get("modele_chemin") or ""), (r.get("modele_nom_fichier") or "")
    # Règle "défaut"
    for r in regles:
        t = (r.get("type") or "").strip().lower()
        if t == "défaut" or t == "defaut" or t == "default":
            return (r.get("modele_chemin") or ""), (r.get("modele_nom_fichier") or "")
    return None


def get_filename_template_for_dest(
    dest_dir_path: str | Path,
    config: dict,
) -> str:
    """
    Retourne le modèle de nom de fichier à utiliser pour le dossier de destination.
    Si config contient formats_par_dossier et qu'un motif correspond au chemin, l'utilise ; sinon modele_nom_fichier.
    """
    default = config.get("modele_nom_fichier") or "{YYYY}-{MM}-{DD}_{type_doc}_{fournisseur}_{numero}_{montant}.pdf"
    formats_par_dossier = config.get("formats_par_dossier") or {}
    dest_str = str(Path(dest_dir_path).resolve()).replace("\\", "/")
    for motif, template in formats_par_dossier.items():
        if not motif or not template:
            continue
        motif_norm = motif.replace("\\", "/").strip("/")
        if motif_norm in dest_str or dest_str.endswith(motif_norm):
            return template
        # Motif peut être un nom de dossier final (ex: A_CLASSER)
        if Path(dest_str).name == motif or motif in Path(dest_str).parts:
            return template
    return default
