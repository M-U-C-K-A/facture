"""
Tests du module data_reader
"""
import pytest
import pandas as pd
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_reader import DataReader, read_data_file


class TestDataReader:
    """Tests pour le DataReader."""

    def test_read_csv_utf8(self, tmp_path):
        """Test lecture CSV UTF-8."""
        csv_content = "nom,valeur\nTest,123\nÉté,456"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        reader = DataReader(csv_file)
        df = reader.read()

        assert len(df) == 2
        assert "nom" in df.columns
        assert "valeur" in df.columns

    def test_read_csv_latin1(self, tmp_path):
        """Test lecture CSV Latin-1."""
        csv_content = "nom,valeur\nCafé,100"
        csv_file = tmp_path / "test.csv"
        csv_file.write_bytes(csv_content.encode("latin-1"))

        reader = DataReader(csv_file)
        df = reader.read()

        assert len(df) == 1

    def test_file_not_found(self):
        """Test fichier introuvable."""
        with pytest.raises(FileNotFoundError):
            DataReader("/chemin/inexistant.csv")

    def test_unsupported_extension(self, tmp_path):
        """Test extension non supportée."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("contenu")

        with pytest.raises(ValueError, match="Extension non supportée"):
            DataReader(txt_file)

    def test_get_columns(self, tmp_path):
        """Test récupération des colonnes."""
        csv_content = "col_a,col_b,col_c\n1,2,3"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        reader = DataReader(csv_file)
        reader.read()
        columns = reader.get_columns()

        assert columns == ["col_a", "col_b", "col_c"]

    def test_get_preview(self, tmp_path):
        """Test aperçu des données."""
        csv_content = "id,nom\n1,A\n2,B\n3,C\n4,D\n5,E\n6,F"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        reader = DataReader(csv_file)
        reader.read()
        preview = reader.get_preview(3)

        assert len(preview) == 3


class TestReadDataFile:
    """Tests pour la fonction utilitaire."""

    def test_read_data_file(self, tmp_path):
        """Test fonction utilitaire."""
        csv_content = "a,b\n1,2"
        csv_file = tmp_path / "data.csv"
        csv_file.write_text(csv_content)

        df = read_data_file(csv_file)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
