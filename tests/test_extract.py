"""
Tests unitaires sur l'extraction : dates, numéro facture, montants.
"""
import pytest
from datetime import date

from basic_scanner.extract import (
    extract_date,
    extract_montant_ttc,
    extract_numero_facture,
    extract_type_document,
    extract_all,
)


class TestExtractDate:
    """Tests extraction de dates (FR + ISO)."""

    def test_date_fr_slash(self):
        texte = "Facture du 31/12/2024"
        assert extract_date(texte) == date(2024, 12, 31)

    def test_date_fr_tiret(self):
        texte = "Date: 15-06-2023"
        assert extract_date(texte) == date(2023, 6, 15)

    def test_date_iso(self):
        texte = "Invoice date 2024-01-15"
        assert extract_date(texte) == date(2024, 1, 15)

    def test_date_fr_long(self):
        texte = "Le 3 décembre 2024 nous avons émis"
        assert extract_date(texte) == date(2024, 12, 3)

    def test_date_annee_2_chiffres(self):
        texte = "Facture 01/03/24"
        assert extract_date(texte) == date(2024, 3, 1)

    def test_pas_de_date(self):
        assert extract_date("Texte sans date") is None


class TestExtractMontant:
    """Tests extraction montant TTC."""

    def test_montant_ttc_explicite(self):
        texte = "Total TTC : 1 234,56 €"
        assert extract_montant_ttc(texte) == 1234.56

    def test_montant_ttc_point_decimal(self):
        texte = "TTC: 999.99 EUR"
        assert extract_montant_ttc(texte) == 999.99

    def test_montant_fallback_eur(self):
        texte = "Montant à payer 42,00 euros"
        assert extract_montant_ttc(texte) == 42.0

    def test_pas_de_montant(self):
        assert extract_montant_ttc("Aucun montant ici") is None


class TestExtractNumeroFacture:
    """Tests extraction numéro de facture."""

    def test_facture_no_fr(self):
        texte = "Facture n° FAC-2024-001"
        assert extract_numero_facture(texte) == "FAC-2024-001"

    def test_invoice_no_en(self):
        texte = "Invoice No: INV/12345"
        assert extract_numero_facture(texte) == "INV/12345"

    def test_numero_alt(self):
        texte = "Réf. n° A12345678"
        num = extract_numero_facture(texte)
        assert num is not None and len(num) >= 4

    def test_pas_de_numero(self):
        assert extract_numero_facture("Pas de numéro") is None


class TestExtractTypeDocument:
    """Tests type document (facture / avoir / inconnu)."""

    def test_facture(self):
        assert extract_type_document("Facture client") == "facture_fournisseur"
        assert extract_type_document("Invoice for services") == "facture_fournisseur"

    def test_avoir(self):
        assert extract_type_document("Avoir n° 123") == "avoir"
        assert extract_type_document("Credit note") == "avoir"

    def test_inconnu(self):
        assert extract_type_document("Document interne") == "inconnu"


class TestExtractAll:
    """Test extraction complète."""

    def test_extract_all_integration(self):
        texte = """
        FACTURE N° FAC-2024-042
        EDF SA
        Date: 15/03/2024
        Total TTC : 1 500,00 €
        """
        data = extract_all(texte)
        assert data.type_document == "facture_fournisseur"
        assert data.date_doc == date(2024, 3, 15)
        assert data.numero_facture == "FAC-2024-042"
        assert data.montant_ttc == 1500.0
