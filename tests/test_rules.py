"""
Tests unitaires pour rules (slugify, placeholders, chemin/nom).
"""
from datetime import date
from pathlib import Path

import pytest

from basic_scanner.models import ExtractedData
from basic_scanner.rules import (
    slugify,
    build_placeholders,
    apply_template,
    build_destination_path,
    build_destination_filename,
)


class TestSlugify:
    """Tests slugify (accents, caractères spéciaux)."""

    def test_accents(self):
        assert slugify("Électricité de France") == "Electricite_de_France"

    def test_espaces_et_speciaux(self):
        assert " " not in slugify("Société  Test & Co")
        assert slugify("a--b  c") == "a_b_c"

    def test_vide(self):
        assert slugify("") == ""


class TestBuildPlaceholders:
    """Tests construction des placeholders à partir de ExtractedData."""

    def test_placeholders_complets(self):
        ext = ExtractedData(
            type_document="facture_fournisseur",
            date_doc=date(2024, 3, 15),
            montant_ttc=1234.56,
            numero_facture="FAC-001",
            fournisseur="EDF",
            fournisseur_raw="EDF SA",
            texte_complet="",
            confidence=0.9,
        )
        p = build_placeholders(ext)
        assert p["YYYY"] == "2024"
        assert p["MM"] == "03"
        assert p["DD"] == "15"
        assert p["fournisseur"] == "EDF"
        # numero est slugifié (tirets → underscores)
        assert p["numero"] == "FAC_001"
        assert p["type_doc"] == "FACT"


class TestApplyTemplate:
    """Tests remplacement des placeholders dans un template."""

    def test_remplacement(self):
        t = "Factures_fournisseurs/{fournisseur}/{YYYY}/{MM}"
        p = {"fournisseur": "EDF", "YYYY": "2024", "MM": "03"}
        assert apply_template(t, p) == "Factures_fournisseurs/EDF/2024/03"

    def test_nom_fichier(self):
        t = "{YYYY}-{MM}-{DD}_{type_doc}_{fournisseur}_{numero}.pdf"
        p = {"YYYY": "2024", "MM": "03", "DD": "15", "type_doc": "FACT", "fournisseur": "EDF", "numero": "FAC-001"}
        assert "2024-03-15_FACT_EDF_FAC-001" in apply_template(t, p)


class TestBuildDestinationPath:
    """Tests construction du chemin de destination."""

    def test_chemin_relatif(self):
        ext = ExtractedData(
            type_document="facture_fournisseur",
            date_doc=date(2024, 3, 15),
            montant_ttc=100.0,
            numero_facture="N1",
            fournisseur="EDF",
            fournisseur_raw="EDF",
            texte_complet="",
            confidence=0.9,
        )
        path = build_destination_path(
            Path("C:/Docs"),
            "Factures_fournisseurs/{fournisseur}/{YYYY}/{MM}",
            ext,
        )
        assert "EDF" in str(path)
        assert "2024" in str(path)
        assert "03" in str(path)
