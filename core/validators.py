"""
Module de validation des données selon le type de document
"""
import pandas as pd
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types de documents supportés."""

    FACTURE = "facture"
    FICHE_PAIE = "fiche_paie"
    CONTRAT = "contrat"


@dataclass
class ValidationResult:
    """Résultat d'une validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    row_index: Optional[int] = None


class DataValidator:
    """
    Validateur de données pour les documents officiels.
    """

    # Colonnes obligatoires par type de document
    REQUIRED_COLUMNS = {
        DocumentType.FACTURE: {
            "client_nom": str,
            "client_adresse": str,
            "designation": str,
            "quantite": (int, float),
            "prix_unitaire_ht": (int, float),
        },
        DocumentType.FICHE_PAIE: {
            "salarie_nom": str,
            "salarie_prenom": str,
            "salaire_brut": (int, float),
            "poste": str,
        },
        DocumentType.CONTRAT: {
            "partie_1_nom": str,
            "partie_2_nom": str,
            "objet_contrat": str,
            "date_debut": str,
        },
    }

    # Colonnes optionnelles par type de document
    OPTIONAL_COLUMNS = {
        DocumentType.FACTURE: {
            "client_siret": str,
            "client_email": str,
            "taux_tva": (int, float),
            "remise_pourcent": (int, float),
            "date_facture": str,
            "date_echeance": str,
            "reference": str,
        },
        DocumentType.FICHE_PAIE: {
            "salarie_matricule": str,
            "date_embauche": str,
            "periode_debut": str,
            "periode_fin": str,
            "heures_travaillees": (int, float),
        },
        DocumentType.CONTRAT: {
            "date_fin": str,
            "montant": (int, float),
            "conditions_particulieres": str,
        },
    }

    def __init__(self, document_type: DocumentType):
        """
        Initialise le validateur pour un type de document.

        Args:
            document_type: Type de document à valider
        """
        self.document_type = document_type
        self.required = self.REQUIRED_COLUMNS[document_type]
        self.optional = self.OPTIONAL_COLUMNS[document_type]

    def validate_structure(self, df: pd.DataFrame) -> ValidationResult:
        """
        Valide la structure du DataFrame (colonnes présentes).

        Args:
            df: DataFrame à valider

        Returns:
            ValidationResult avec les erreurs/warnings
        """
        errors = []
        warnings = []

        # Normaliser les noms de colonnes
        columns = set(df.columns.str.strip().str.lower())

        # Vérifier les colonnes obligatoires
        for col in self.required.keys():
            if col not in columns:
                errors.append(f"Colonne obligatoire manquante : '{col}'")

        # Vérifier les colonnes optionnelles (avertissement)
        for col in self.optional.keys():
            if col not in columns:
                warnings.append(f"Colonne optionnelle absente : '{col}'")

        # Colonnes inconnues
        all_known = set(self.required.keys()) | set(self.optional.keys())
        unknown = columns - all_known
        if unknown:
            warnings.append(f"Colonnes non reconnues (ignorées) : {', '.join(unknown)}")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def validate_row(self, row: pd.Series, row_index: int) -> ValidationResult:
        """
        Valide une ligne de données.

        Args:
            row: Ligne du DataFrame
            row_index: Index de la ligne

        Returns:
            ValidationResult avec les erreurs/warnings
        """
        errors = []
        warnings = []

        for col, expected_type in self.required.items():
            if col in row.index:
                value = row[col]

                # Vérifier les valeurs nulles
                if pd.isna(value) or value == "":
                    errors.append(f"Ligne {row_index + 1} : '{col}' est vide")
                    continue

                # Vérifier le type
                if not isinstance(value, expected_type):
                    # Tenter une conversion
                    try:
                        if expected_type in [(int, float), float]:
                            float(value)
                        elif expected_type == int:
                            int(value)
                    except (ValueError, TypeError):
                        errors.append(
                            f"Ligne {row_index + 1} : '{col}' type incorrect "
                            f"(attendu: {expected_type}, reçu: {type(value).__name__})"
                        )

        # Validations spécifiques par type de document
        if self.document_type == DocumentType.FACTURE:
            errors.extend(self._validate_facture_row(row, row_index))
        elif self.document_type == DocumentType.FICHE_PAIE:
            errors.extend(self._validate_paie_row(row, row_index))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            row_index=row_index,
        )

    def _validate_facture_row(self, row: pd.Series, row_index: int) -> List[str]:
        """Validations spécifiques aux factures."""
        errors = []

        # Vérifier que quantité > 0
        if "quantite" in row.index:
            try:
                if float(row["quantite"]) <= 0:
                    errors.append(f"Ligne {row_index + 1} : quantité doit être > 0")
            except (ValueError, TypeError):
                pass

        # Vérifier que prix_unitaire_ht >= 0
        if "prix_unitaire_ht" in row.index:
            try:
                if float(row["prix_unitaire_ht"]) < 0:
                    errors.append(
                        f"Ligne {row_index + 1} : prix_unitaire_ht ne peut être négatif"
                    )
            except (ValueError, TypeError):
                pass

        # Valider le SIRET si présent
        if "client_siret" in row.index and not pd.isna(row.get("client_siret")):
            siret = str(row["client_siret"]).replace(" ", "").replace("-", "")
            if not re.match(r"^\d{14}$", siret):
                errors.append(
                    f"Ligne {row_index + 1} : SIRET invalide (14 chiffres attendus)"
                )

        # Valider le taux de TVA si présent
        if "taux_tva" in row.index and not pd.isna(row.get("taux_tva")):
            try:
                tva = float(row["taux_tva"])
                if tva < 0 or tva > 100:
                    errors.append(
                        f"Ligne {row_index + 1} : taux_tva doit être entre 0 et 100"
                    )
            except (ValueError, TypeError):
                pass

        return errors

    def _validate_paie_row(self, row: pd.Series, row_index: int) -> List[str]:
        """Validations spécifiques aux fiches de paie."""
        errors = []

        # Vérifier que salaire_brut > 0
        if "salaire_brut" in row.index:
            try:
                if float(row["salaire_brut"]) <= 0:
                    errors.append(f"Ligne {row_index + 1} : salaire_brut doit être > 0")
            except (ValueError, TypeError):
                pass

        return errors

    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[bool, List[ValidationResult]]:
        """
        Valide l'ensemble du DataFrame.

        Args:
            df: DataFrame à valider

        Returns:
            Tuple (is_valid, list of ValidationResult)
        """
        results = []

        # Valider la structure
        structure_result = self.validate_structure(df)
        results.append(structure_result)

        if not structure_result.is_valid:
            logger.error("Erreurs de structure détectées")
            for error in structure_result.errors:
                logger.error(f"  - {error}")
            return False, results

        # Valider chaque ligne
        all_valid = True
        for idx, row in df.iterrows():
            row_result = self.validate_row(row, idx)
            if not row_result.is_valid:
                all_valid = False
                results.append(row_result)
                for error in row_result.errors:
                    logger.error(f"  - {error}")

        if all_valid:
            logger.info(f"Validation réussie : {len(df)} lignes validées")

        return all_valid, results


# Fonction utilitaire
def validate_data(
    df: pd.DataFrame, document_type: str | DocumentType
) -> Tuple[bool, List[ValidationResult]]:
    """
    Valide un DataFrame pour un type de document.

    Args:
        df: DataFrame à valider
        document_type: Type de document ("facture", "fiche_paie", "contrat")

    Returns:
        Tuple (is_valid, list of ValidationResult)
    """
    if isinstance(document_type, str):
        document_type = DocumentType(document_type.lower())

    validator = DataValidator(document_type)
    return validator.validate_dataframe(df)
