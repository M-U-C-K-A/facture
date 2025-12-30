"""
Module de lecture des fichiers CSV et Excel
"""
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataReader:
    """
    Lecteur de fichiers de données avec support multi-format et multi-encodage.
    """

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
    SUPPORTED_ENCODINGS = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

    def __init__(self, file_path: str | Path):
        """
        Initialise le lecteur avec le chemin du fichier.

        Args:
            file_path: Chemin vers le fichier CSV ou Excel
        """
        self.file_path = Path(file_path)
        self._validate_file()
        self.data: Optional[pd.DataFrame] = None

    def _validate_file(self) -> None:
        """Vérifie que le fichier existe et a une extension supportée."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {self.file_path}")

        if self.file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Extension non supportée : {self.file_path.suffix}. "
                f"Extensions acceptées : {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

    def read(self, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Lit le fichier et retourne un DataFrame.

        Args:
            sheet_name: Nom de la feuille Excel (ignoré pour CSV)

        Returns:
            DataFrame contenant les données
        """
        extension = self.file_path.suffix.lower()

        if extension == ".csv":
            self.data = self._read_csv()
        else:
            self.data = self._read_excel(sheet_name)

        # Nettoyage des colonnes
        self.data.columns = self.data.columns.str.strip().str.lower()

        logger.info(
            f"Fichier lu avec succès : {len(self.data)} lignes, "
            f"{len(self.data.columns)} colonnes"
        )

        return self.data

    def _read_csv(self) -> pd.DataFrame:
        """
        Lit un fichier CSV avec détection automatique de l'encodage.

        Returns:
            DataFrame contenant les données
        """
        for encoding in self.SUPPORTED_ENCODINGS:
            try:
                df = pd.read_csv(
                    self.file_path,
                    encoding=encoding,
                    sep=None,  # Détection automatique du séparateur
                    engine="python",
                    on_bad_lines="warn",
                )
                logger.info(f"Encodage détecté : {encoding}")
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Erreur avec encodage {encoding} : {e}")
                continue

        raise ValueError(
            f"Impossible de lire le fichier avec les encodages : "
            f"{', '.join(self.SUPPORTED_ENCODINGS)}"
        )

    def _read_excel(self, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Lit un fichier Excel.

        Args:
            sheet_name: Nom de la feuille (première feuille par défaut)

        Returns:
            DataFrame contenant les données
        """
        try:
            df = pd.read_excel(
                self.file_path,
                sheet_name=sheet_name or 0,
                engine="openpyxl",
            )
            return df
        except Exception as e:
            raise ValueError(f"Erreur lors de la lecture Excel : {e}")

    def get_columns(self) -> list[str]:
        """Retourne la liste des colonnes du fichier."""
        if self.data is None:
            self.read()
        return list(self.data.columns)

    def get_preview(self, n_rows: int = 5) -> pd.DataFrame:
        """
        Retourne un aperçu des premières lignes.

        Args:
            n_rows: Nombre de lignes à afficher

        Returns:
            DataFrame avec les n premières lignes
        """
        if self.data is None:
            self.read()
        return self.data.head(n_rows)

    def get_row_count(self) -> int:
        """Retourne le nombre de lignes."""
        if self.data is None:
            self.read()
        return len(self.data)


# Fonction utilitaire pour lecture rapide
def read_data_file(
    file_path: str | Path, sheet_name: Optional[str] = None
) -> pd.DataFrame:
    """
    Lit un fichier de données (CSV ou Excel) et retourne un DataFrame.

    Args:
        file_path: Chemin vers le fichier
        sheet_name: Nom de la feuille Excel (optionnel)

    Returns:
        DataFrame contenant les données
    """
    reader = DataReader(file_path)
    return reader.read(sheet_name)
