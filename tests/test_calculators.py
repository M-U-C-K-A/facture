"""
Tests du module calculators
"""
import pytest
from decimal import Decimal
from pathlib import Path
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.calculators import (
    LigneFacture,
    CalculatorFacture,
    CalculatorPaie,
    calculer_tva,
    calculer_ttc,
    arrondir_legal,
)


class TestLigneFacture:
    """Tests pour LigneFacture."""

    def test_montant_ht_simple(self):
        """Test calcul montant HT simple."""
        ligne = LigneFacture(
            designation="Service",
            quantite=2,
            prix_unitaire_ht=100.0,
        )
        assert ligne.montant_ht == Decimal("200.00")

    def test_montant_ht_avec_remise(self):
        """Test calcul montant HT avec remise."""
        ligne = LigneFacture(
            designation="Service",
            quantite=1,
            prix_unitaire_ht=100.0,
            remise_pourcent=10.0,
        )
        assert ligne.montant_ht == Decimal("90.00")

    def test_montant_tva(self):
        """Test calcul TVA."""
        ligne = LigneFacture(
            designation="Service",
            quantite=1,
            prix_unitaire_ht=100.0,
            taux_tva=20.0,
        )
        assert ligne.montant_tva == Decimal("20.00")

    def test_montant_ttc(self):
        """Test calcul TTC."""
        ligne = LigneFacture(
            designation="Service",
            quantite=1,
            prix_unitaire_ht=100.0,
            taux_tva=20.0,
        )
        assert ligne.montant_ttc == Decimal("120.00")

    def test_to_dict(self):
        """Test conversion en dictionnaire."""
        ligne = LigneFacture(
            designation="Test",
            quantite=1,
            prix_unitaire_ht=100.0,
        )
        d = ligne.to_dict()
        
        assert "designation" in d
        assert "montant_ht" in d
        assert "montant_ttc" in d


class TestCalculatorFacture:
    """Tests pour CalculatorFacture."""

    def test_totaux(self):
        """Test calcul des totaux."""
        lignes = [
            LigneFacture("Service A", 1, 100.0, 20.0),
            LigneFacture("Service B", 2, 50.0, 20.0),
        ]
        calc = CalculatorFacture(lignes)

        assert calc.total_ht == Decimal("200.00")
        assert calc.total_tva == Decimal("40.00")
        assert calc.total_ttc == Decimal("240.00")

    def test_from_dataframe(self):
        """Test création depuis DataFrame."""
        df = pd.DataFrame({
            "designation": ["A", "B"],
            "quantite": [1, 2],
            "prix_unitaire_ht": [100, 50],
            "taux_tva": [20, 20],
        })
        calc = CalculatorFacture.from_dataframe(df)

        assert len(calc.lignes) == 2
        assert calc.total_ht == Decimal("200.00")

    def test_tva_par_taux(self):
        """Test groupement TVA par taux."""
        lignes = [
            LigneFacture("A", 1, 100.0, 20.0),
            LigneFacture("B", 1, 100.0, 10.0),
        ]
        calc = CalculatorFacture(lignes)
        tva = calc.get_tva_par_taux()

        assert 20.0 in tva
        assert 10.0 in tva
        assert tva[20.0]["tva"] == Decimal("20.00")
        assert tva[10.0]["tva"] == Decimal("10.00")


class TestCalculatorPaie:
    """Tests pour CalculatorPaie."""

    def test_salaire_net(self):
        """Test calcul salaire net."""
        calc = CalculatorPaie(salaire_brut=3000.0)

        # Le net doit être inférieur au brut
        assert calc.salaire_net_avant_impot < Decimal("3000.00")
        assert calc.salaire_net_avant_impot > Decimal("2000.00")

    def test_cout_employeur(self):
        """Test coût total employeur."""
        calc = CalculatorPaie(salaire_brut=3000.0)

        # Le coût employeur doit être supérieur au brut
        assert calc.cout_total_employeur > Decimal("3000.00")

    def test_to_dict(self):
        """Test conversion en dictionnaire."""
        calc = CalculatorPaie(salaire_brut=2500.0)
        d = calc.to_dict()

        assert "salaire_brut" in d
        assert "cotisations" in d
        assert "salaire_net_avant_impot" in d
        assert len(d["cotisations"]) > 0


class TestFonctionsUtilitaires:
    """Tests des fonctions utilitaires."""

    def test_calculer_tva(self):
        """Test calcul TVA."""
        assert calculer_tva(100, 20) == 20.0
        assert calculer_tva(150, 10) == 15.0

    def test_calculer_ttc(self):
        """Test calcul TTC."""
        assert calculer_ttc(100, 20) == 120.0
        assert calculer_ttc(200, 5.5) == 211.0

    def test_arrondir_legal(self):
        """Test arrondi légal."""
        assert arrondir_legal(10.555) == 10.56
        assert arrondir_legal(10.554) == 10.55
        assert arrondir_legal(10.5) == 10.5
