"""
Modèles de données (dataclasses) pour le pipeline de traitement.
"""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass
class ExtractedData:
    """Données extraites d'un document PDF après OCR/parsing."""

    type_document: str  # facture_fournisseur | avoir | inconnu
    date_doc: Optional[date] = None
    montant_ttc: Optional[float] = None
    numero_facture: Optional[str] = None
    fournisseur: Optional[str] = None
    fournisseur_raw: Optional[str] = None  # texte brut trouvé avant matching
    texte_complet: str = ""
    confidence: float = 0.0  # 0..1

    def to_dict(self) -> dict:
        """Sérialisation pour JSON (dates en ISO)."""
        return {
            "type_document": self.type_document,
            "date_doc": self.date_doc.isoformat() if self.date_doc else None,
            "montant_ttc": self.montant_ttc,
            "numero_facture": self.numero_facture,
            "fournisseur": self.fournisseur,
            "fournisseur_raw": self.fournisseur_raw,
            "confidence": self.confidence,
        }


@dataclass
class ProcessingResult:
    """Résultat du traitement d'un fichier (chemin destination, métadonnées)."""

    source_path: Path
    dest_dir: Path
    dest_filename: str
    extracted: ExtractedData
    moved: bool = False
    error: Optional[str] = None

    def dest_path(self) -> Path:
        return self.dest_dir / self.dest_filename


@dataclass
class WatcherConfig:
    """Configuration de la surveillance (stabilité fichier, exclusions)."""

    inbox_path: Path
    stability_seconds: float = 5.0
    stability_check_interval: float = 1.0
    min_file_size: int = 0
    exclude_patterns: list[str] = field(default_factory=lambda: ["*.tmp", "~*", "*.part"])
