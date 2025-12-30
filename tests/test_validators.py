"""
Tests du module validators
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.validators import DataValidator, DocumentType, validate_data


class TestDataValidator:
    """Tests pour le DataValidator."""

    def test_validate_facture_structure_valid(self):
        """Test validation structure facture valide."""
        df = pd.DataFrame({
            "client_nom": ["Test"],
            "client_adresse": ["123 Rue"],
            "designation": ["Service"],
            "quantite": [1],
            "prix_unitaire_ht": [100.0],
        })

        validator = DataValidator(DocumentType.FACTURE)
        result = validator.validate_structure(df)

        assert result.is_valid

    def test_validate_facture_structure_missing_column(self):
        """Test validation structure avec colonne manquante."""
        df = pd.DataFrame({
            "client_nom": ["Test"],
            # client_adresse manquant
            "designation": ["Service"],
            "quantite": [1],
            "prix_unitaire_ht": [100.0],
        })

        validator = DataValidator(DocumentType.FACTURE)
        result = validator.validate_structure(df)

        assert not result.is_valid
        assert any("client_adresse" in e for e in result.errors)

    def test_validate_row_valid(self):
        """Test validation ligne valide."""
        row = pd.Series({
            "client_nom": "Client Test",
            "client_adresse": "123 Rue Test",
            "designation": "Service test",
            "quantite": 2,
            "prix_unitaire_ht": 150.0,
        })

        validator = DataValidator(DocumentType.FACTURE)
        result = validator.validate_row(row, 0)

        assert result.is_valid

    def test_validate_row_empty_value(self):
        """Test validation valeur vide."""
        row = pd.Series({
            "client_nom": "",  # Vide
            "client_adresse": "123 Rue",
            "designation": "Service",
            "quantite": 1,
            "prix_unitaire_ht": 100.0,
        })

        validator = DataValidator(DocumentType.FACTURE)
        result = validator.validate_row(row, 0)

        assert not result.is_valid

    def test_validate_row_negative_quantity(self):
        """Test quantité négative."""
        row = pd.Series({
            "client_nom": "Test",
            "client_adresse": "123 Rue",
            "designation": "Service",
            "quantite": -1,  # Négatif
            "prix_unitaire_ht": 100.0,
        })

        validator = DataValidator(DocumentType.FACTURE)
        result = validator.validate_row(row, 0)

        assert not result.is_valid

    def test_validate_siret_invalid(self):
        """Test SIRET invalide."""
        row = pd.Series({
            "client_nom": "Test",
            "client_adresse": "123 Rue",
            "designation": "Service",
            "quantite": 1,
            "prix_unitaire_ht": 100.0,
            "client_siret": "123",  # SIRET invalide
        })

        validator = DataValidator(DocumentType.FACTURE)
        result = validator.validate_row(row, 0)

        assert not result.is_valid


class TestValidateData:
    """Tests pour la fonction validate_data."""

    def test_validate_data_string_type(self):
        """Test avec type en string."""
        df = pd.DataFrame({
            "client_nom": ["Test"],
            "client_adresse": ["Rue"],
            "designation": ["Service"],
            "quantite": [1],
            "prix_unitaire_ht": [100],
        })

        is_valid, _ = validate_data(df, "facture")
        assert is_valid
