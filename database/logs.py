"""
Module de gestion des logs et numérotation séquentielle avec SQLite
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# Import des paramètres
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DATABASE_PATH, INVOICE_PREFIX, PAYSLIP_PREFIX, CONTRACT_PREFIX, CURRENT_YEAR

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types de documents."""

    FACTURE = "facture"
    FICHE_PAIE = "fiche_paie"
    CONTRAT = "contrat"


@dataclass
class DocumentLog:
    """Représente un enregistrement de document."""

    id: Optional[int]
    document_type: str
    document_number: str
    filename: str
    client_name: str
    total_amount: float
    created_at: datetime
    source_file: str
    status: str = "generated"


class DatabaseManager:
    """Gestionnaire de base de données SQLite."""

    def __init__(self, db_path: Path = DATABASE_PATH):
        """
        Initialise le gestionnaire de base de données.

        Args:
            db_path: Chemin vers le fichier SQLite
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Crée et retourne une connexion à la base."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Initialise les tables de la base de données."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Table des documents générés
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_type TEXT NOT NULL,
                    document_number TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    client_name TEXT,
                    total_amount REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_file TEXT,
                    status TEXT DEFAULT 'generated'
                )
            """)

            # Table de numérotation séquentielle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS numbering (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_type TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    last_number INTEGER DEFAULT 0,
                    UNIQUE(document_type, year)
                )
            """)

            # Index pour les recherches
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_type 
                ON documents(document_type)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_number 
                ON documents(document_number)
            """)

            conn.commit()

        logger.info(f"Base de données initialisée : {self.db_path}")

    def get_next_number(self, document_type: DocumentType, year: int = CURRENT_YEAR) -> str:
        """
        Génère le prochain numéro séquentiel pour un type de document.

        Args:
            document_type: Type de document
            year: Année de référence

        Returns:
            Numéro formaté (ex: FAC-2024-00001)
        """
        prefixes = {
            DocumentType.FACTURE: INVOICE_PREFIX,
            DocumentType.FICHE_PAIE: PAYSLIP_PREFIX,
            DocumentType.CONTRAT: CONTRACT_PREFIX,
        }

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Récupérer et incrémenter le numéro
            cursor.execute("""
                INSERT INTO numbering (document_type, year, last_number)
                VALUES (?, ?, 1)
                ON CONFLICT(document_type, year) DO UPDATE SET 
                    last_number = last_number + 1
                RETURNING last_number
            """, (document_type.value, year))

            result = cursor.fetchone()
            number = result["last_number"] if result else 1

            conn.commit()

        prefix = prefixes.get(document_type, "DOC")
        return f"{prefix}-{year}-{number:05d}"

    def log_document(self, doc: DocumentLog) -> int:
        """
        Enregistre un document dans les logs.

        Args:
            doc: Objet DocumentLog à enregistrer

        Returns:
            ID de l'enregistrement créé
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO documents (
                    document_type, document_number, filename,
                    client_name, total_amount, source_file, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.document_type,
                doc.document_number,
                doc.filename,
                doc.client_name,
                doc.total_amount,
                doc.source_file,
                doc.status,
            ))

            conn.commit()
            doc_id = cursor.lastrowid

        logger.info(f"Document enregistré : {doc.document_number} (ID: {doc_id})")
        return doc_id

    def get_document_by_number(self, document_number: str) -> Optional[DocumentLog]:
        """
        Récupère un document par son numéro.

        Args:
            document_number: Numéro du document

        Returns:
            DocumentLog ou None si non trouvé
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM documents WHERE document_number = ?
            """, (document_number,))

            row = cursor.fetchone()

            if row:
                return DocumentLog(
                    id=row["id"],
                    document_type=row["document_type"],
                    document_number=row["document_number"],
                    filename=row["filename"],
                    client_name=row["client_name"],
                    total_amount=row["total_amount"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    source_file=row["source_file"],
                    status=row["status"],
                )

        return None

    def get_documents_by_type(
        self,
        document_type: DocumentType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentLog]:
        """
        Récupère les documents par type.

        Args:
            document_type: Type de document
            limit: Nombre maximum de résultats
            offset: Décalage pour la pagination

        Returns:
            Liste de DocumentLog
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM documents 
                WHERE document_type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (document_type.value, limit, offset))

            documents = []
            for row in cursor.fetchall():
                documents.append(DocumentLog(
                    id=row["id"],
                    document_type=row["document_type"],
                    document_number=row["document_number"],
                    filename=row["filename"],
                    client_name=row["client_name"],
                    total_amount=row["total_amount"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    source_file=row["source_file"],
                    status=row["status"],
                ))

            return documents

    def get_stats(self) -> dict:
        """
        Récupère les statistiques de génération.

        Returns:
            Dictionnaire avec les statistiques
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total par type
            cursor.execute("""
                SELECT document_type, COUNT(*) as count, SUM(total_amount) as total
                FROM documents
                GROUP BY document_type
            """)

            for row in cursor.fetchall():
                stats[row["document_type"]] = {
                    "count": row["count"],
                    "total_amount": row["total"] or 0,
                }

            # Total global
            cursor.execute("SELECT COUNT(*) as count FROM documents")
            stats["total_documents"] = cursor.fetchone()["count"]

            return stats


# Instance globale
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Retourne l'instance globale du gestionnaire de base de données."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


# Fonctions utilitaires
def get_next_invoice_number() -> str:
    """Génère le prochain numéro de facture."""
    return get_db_manager().get_next_number(DocumentType.FACTURE)


def get_next_payslip_number() -> str:
    """Génère le prochain numéro de fiche de paie."""
    return get_db_manager().get_next_number(DocumentType.FICHE_PAIE)


def get_next_contract_number() -> str:
    """Génère le prochain numéro de contrat."""
    return get_db_manager().get_next_number(DocumentType.CONTRAT)


def log_document(
    document_type: str,
    document_number: str,
    filename: str,
    client_name: str = "",
    total_amount: float = 0.0,
    source_file: str = "",
) -> int:
    """
    Enregistre un document généré dans les logs.

    Returns:
        ID de l'enregistrement
    """
    doc = DocumentLog(
        id=None,
        document_type=document_type,
        document_number=document_number,
        filename=filename,
        client_name=client_name,
        total_amount=total_amount,
        created_at=datetime.now(),
        source_file=source_file,
    )
    return get_db_manager().log_document(doc)
