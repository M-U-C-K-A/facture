"""
Module de calcul automatique (TVA, cotisations sociales, totaux)
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from dataclasses import dataclass
import pandas as pd

# Import des paramètres de configuration
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DEFAULT_TVA_RATES, COTISATIONS_SOCIALES


@dataclass
class LigneFacture:
    """Représente une ligne de facture avec calculs."""

    designation: str
    quantite: float
    prix_unitaire_ht: float
    taux_tva: float = 20.0
    remise_pourcent: float = 0.0

    @property
    def montant_ht(self) -> Decimal:
        """Calcule le montant HT de la ligne."""
        montant = Decimal(str(self.quantite)) * Decimal(str(self.prix_unitaire_ht))
        if self.remise_pourcent > 0:
            remise = montant * Decimal(str(self.remise_pourcent)) / Decimal("100")
            montant -= remise
        return montant.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def montant_tva(self) -> Decimal:
        """Calcule le montant de TVA."""
        tva = self.montant_ht * Decimal(str(self.taux_tva)) / Decimal("100")
        return tva.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def montant_ttc(self) -> Decimal:
        """Calcule le montant TTC."""
        return self.montant_ht + self.montant_tva

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour le template."""
        return {
            "designation": self.designation,
            "quantite": self.quantite,
            "prix_unitaire_ht": float(self.prix_unitaire_ht),
            "taux_tva": self.taux_tva,
            "remise_pourcent": self.remise_pourcent,
            "montant_ht": float(self.montant_ht),
            "montant_tva": float(self.montant_tva),
            "montant_ttc": float(self.montant_ttc),
        }


class CalculatorFacture:
    """Calculatrice pour les factures."""

    def __init__(self, lignes: List[LigneFacture]):
        """
        Initialise la calculatrice avec les lignes de facture.

        Args:
            lignes: Liste des lignes de facture
        """
        self.lignes = lignes

    @classmethod
    def from_dataframe(
        cls, df: pd.DataFrame, taux_tva_defaut: float = 20.0
    ) -> "CalculatorFacture":
        """
        Crée une calculatrice à partir d'un DataFrame.

        Args:
            df: DataFrame avec les colonnes de facture
            taux_tva_defaut: Taux de TVA par défaut si non spécifié

        Returns:
            Instance de CalculatorFacture
        """
        lignes = []
        for _, row in df.iterrows():
            ligne = LigneFacture(
                designation=str(row.get("designation", "")),
                quantite=float(row.get("quantite", 1)),
                prix_unitaire_ht=float(row.get("prix_unitaire_ht", 0)),
                taux_tva=float(row.get("taux_tva", taux_tva_defaut)),
                remise_pourcent=float(row.get("remise_pourcent", 0)),
            )
            lignes.append(ligne)
        return cls(lignes)

    @property
    def total_ht(self) -> Decimal:
        """Calcule le total HT de la facture."""
        total = sum(ligne.montant_ht for ligne in self.lignes)
        return Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_tva(self) -> Decimal:
        """Calcule le total de TVA."""
        total = sum(ligne.montant_tva for ligne in self.lignes)
        return Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_ttc(self) -> Decimal:
        """Calcule le total TTC."""
        return self.total_ht + self.total_tva

    def get_tva_par_taux(self) -> Dict[float, Dict[str, Decimal]]:
        """
        Calcule les montants de TVA regroupés par taux.

        Returns:
            Dict avec taux comme clé et dict(base, tva) comme valeur
        """
        tva_par_taux = {}
        for ligne in self.lignes:
            taux = ligne.taux_tva
            if taux not in tva_par_taux:
                tva_par_taux[taux] = {"base": Decimal("0"), "tva": Decimal("0")}
            tva_par_taux[taux]["base"] += ligne.montant_ht
            tva_par_taux[taux]["tva"] += ligne.montant_tva

        return tva_par_taux

    def to_dict(self) -> Dict:
        """Convertit tous les calculs en dictionnaire pour le template."""
        return {
            "lignes": [ligne.to_dict() for ligne in self.lignes],
            "total_ht": float(self.total_ht),
            "total_tva": float(self.total_tva),
            "total_ttc": float(self.total_ttc),
            "tva_par_taux": {
                taux: {"base": float(vals["base"]), "tva": float(vals["tva"])}
                for taux, vals in self.get_tva_par_taux().items()
            },
        }


@dataclass
class CotisationSociale:
    """Représente une cotisation sociale."""

    libelle: str
    base: Decimal
    taux_salarie: float
    taux_employeur: float

    @property
    def part_salarie(self) -> Decimal:
        """Calcule la part salarié."""
        montant = self.base * Decimal(str(self.taux_salarie)) / Decimal("100")
        return montant.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def part_employeur(self) -> Decimal:
        """Calcule la part employeur."""
        montant = self.base * Decimal(str(self.taux_employeur)) / Decimal("100")
        return montant.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour le template."""
        return {
            "libelle": self.libelle,
            "base": float(self.base),
            "taux_salarie": self.taux_salarie,
            "taux_employeur": self.taux_employeur,
            "part_salarie": float(self.part_salarie),
            "part_employeur": float(self.part_employeur),
        }


class CalculatorPaie:
    """Calculatrice pour les fiches de paie (barèmes 2024 simplifiés)."""

    # Plafond mensuel de la Sécurité Sociale 2024
    PMSS_2024 = Decimal("3864")

    # Cotisations avec taux salarié et employeur
    COTISATIONS = [
        ("Santé - Maladie", 0.0, 7.00),
        ("Accidents du travail", 0.0, 2.21),
        ("Retraite - Vieillesse plafonnée", 6.90, 8.55),
        ("Retraite - Vieillesse déplafonnée", 0.40, 2.02),
        ("Famille", 0.0, 3.45),
        ("Chômage", 0.0, 4.05),
        ("Retraite complémentaire T1", 3.15, 4.72),
        ("CSG déductible", 6.80, 0.0),
        ("CSG non déductible", 2.40, 0.0),
        ("CRDS", 0.50, 0.0),
    ]

    def __init__(self, salaire_brut: float, heures_travaillees: float = 151.67):
        """
        Initialise la calculatrice de paie.

        Args:
            salaire_brut: Salaire brut mensuel
            heures_travaillees: Heures travaillées dans le mois
        """
        self.salaire_brut = Decimal(str(salaire_brut))
        self.heures_travaillees = heures_travaillees
        self.cotisations: List[CotisationSociale] = []
        self._calculer_cotisations()

    def _calculer_cotisations(self) -> None:
        """Calcule toutes les cotisations sociales."""
        for libelle, taux_salarie, taux_employeur in self.COTISATIONS:
            # Utiliser le plafond pour les cotisations plafonnées
            if "plafonnée" in libelle.lower():
                base = min(self.salaire_brut, self.PMSS_2024)
            else:
                base = self.salaire_brut

            cotisation = CotisationSociale(
                libelle=libelle,
                base=base,
                taux_salarie=taux_salarie,
                taux_employeur=taux_employeur,
            )
            self.cotisations.append(cotisation)

    @property
    def total_cotisations_salarie(self) -> Decimal:
        """Calcule le total des cotisations salarié."""
        total = sum(c.part_salarie for c in self.cotisations)
        return Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_cotisations_employeur(self) -> Decimal:
        """Calcule le total des cotisations employeur."""
        total = sum(c.part_employeur for c in self.cotisations)
        return Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def salaire_net_avant_impot(self) -> Decimal:
        """Calcule le salaire net avant impôt."""
        net = self.salaire_brut - self.total_cotisations_salarie
        return net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def montant_net_social(self) -> Decimal:
        """
        Calcule le Montant Net Social (MNS).
        Obligatoire sur les bulletins depuis juillet 2023.
        = Salaire brut - cotisations sociales obligatoires (hors CSG/CRDS non déductibles)
        """
        # Cotisations qui réduisent le net social
        cotisations_net_social = Decimal("0")
        for c in self.cotisations:
            # Exclure CSG non déductible et CRDS du calcul
            if "non déductible" not in c.libelle.lower() and "crds" not in c.libelle.lower():
                cotisations_net_social += c.part_salarie
        
        mns = self.salaire_brut - cotisations_net_social
        return mns.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def cout_total_employeur(self) -> Decimal:
        """Calcule le coût total pour l'employeur."""
        cout = self.salaire_brut + self.total_cotisations_employeur
        return cout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def to_dict(self) -> Dict:
        """Convertit tous les calculs en dictionnaire pour le template."""
        return {
            "salaire_brut": float(self.salaire_brut),
            "heures_travaillees": self.heures_travaillees,
            "cotisations": [c.to_dict() for c in self.cotisations],
            "total_cotisations_salarie": float(self.total_cotisations_salarie),
            "total_cotisations_employeur": float(self.total_cotisations_employeur),
            "salaire_net_avant_impot": float(self.salaire_net_avant_impot),
            "montant_net_social": float(self.montant_net_social),
            "cout_total_employeur": float(self.cout_total_employeur),
        }


# Fonctions utilitaires
def calculer_tva(montant_ht: float, taux: float = 20.0) -> float:
    """
    Calcule le montant de TVA.

    Args:
        montant_ht: Montant HT
        taux: Taux de TVA en pourcentage

    Returns:
        Montant de TVA arrondi à 2 décimales
    """
    tva = Decimal(str(montant_ht)) * Decimal(str(taux)) / Decimal("100")
    return float(tva.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculer_ttc(montant_ht: float, taux_tva: float = 20.0) -> float:
    """
    Calcule le montant TTC.

    Args:
        montant_ht: Montant HT
        taux_tva: Taux de TVA en pourcentage

    Returns:
        Montant TTC arrondi à 2 décimales
    """
    return montant_ht + calculer_tva(montant_ht, taux_tva)


def arrondir_legal(montant: float) -> float:
    """
    Arrondit un montant selon les règles légales (2 décimales, arrondi au plus proche).

    Args:
        montant: Montant à arrondir

    Returns:
        Montant arrondi
    """
    return float(
        Decimal(str(montant)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )
