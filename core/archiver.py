"""
Module d'archivage légal avec compression et hash d'intégrité
"""
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class ArchiveurLegal:
    """
    Archiveur légal pour les documents comptables.
    Génère des archives ZIP datées avec fichier de contrôle d'intégrité.
    """
    
    def __init__(self, archive_dir: Path):
        """
        Initialise l'archiveur.
        
        Args:
            archive_dir: Dossier de destination des archives
        """
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def create_archive(
        self,
        files: List[Path],
        archive_name: Optional[str] = None,
        period: Optional[str] = None,
    ) -> Path:
        """
        Crée une archive ZIP avec les fichiers spécifiés.
        
        Args:
            files: Liste des fichiers à archiver
            archive_name: Nom personnalisé de l'archive
            period: Période (ex: "2024-12")
            
        Returns:
            Chemin vers l'archive créée
        """
        # Nom de l'archive
        if archive_name is None:
            period = period or datetime.now().strftime("%Y-%m")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"archive_documents_{period}_{timestamp}"
        
        archive_path = self.archive_dir / f"{archive_name}.zip"
        
        # Créer le fichier manifest
        manifest = {
            "created_at": datetime.now().isoformat(),
            "period": period,
            "files": [],
        }
        
        # Créer l'archive ZIP
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                if file_path.exists():
                    # Calculer le hash SHA256
                    file_hash = self._compute_hash(file_path)
                    
                    # Ajouter au ZIP
                    zf.write(file_path, file_path.name)
                    
                    # Ajouter au manifest
                    manifest["files"].append({
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "sha256": file_hash,
                        "created": datetime.fromtimestamp(
                            file_path.stat().st_ctime
                        ).isoformat(),
                    })
                else:
                    logger.warning(f"Fichier non trouvé : {file_path}")
            
            # Ajouter le manifest au ZIP
            manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)
            zf.writestr("manifest.json", manifest_json)
        
        # Calculer le hash de l'archive complète
        archive_hash = self._compute_hash(archive_path)
        
        # Créer le fichier de contrôle externe
        control_file = archive_path.with_suffix(".sha256")
        control_file.write_text(f"{archive_hash}  {archive_path.name}\n")
        
        logger.info(f"Archive créée : {archive_path}")
        logger.info(f"Hash SHA256 : {archive_hash}")
        
        return archive_path
    
    def archive_month(
        self,
        source_dir: Path,
        year: int = None,
        month: int = None,
        pattern: str = "*.pdf",
    ) -> Path:
        """
        Archive tous les documents d'un mois.
        
        Args:
            source_dir: Dossier source des documents
            year: Année (courante par défaut)
            month: Mois (courant par défaut)
            pattern: Pattern de fichiers à archiver
            
        Returns:
            Chemin vers l'archive
        """
        year = year or datetime.now().year
        month = month or datetime.now().month
        period = f"{year}-{month:02d}"
        
        # Trouver les fichiers
        source_dir = Path(source_dir)
        files = list(source_dir.glob(pattern))
        
        if not files:
            logger.warning(f"Aucun fichier trouvé dans {source_dir}")
            return None
        
        return self.create_archive(
            files=files,
            archive_name=f"archive_factures_{period}",
            period=period,
        )
    
    def verify_archive(self, archive_path: Path) -> bool:
        """
        Vérifie l'intégrité d'une archive.
        
        Args:
            archive_path: Chemin de l'archive à vérifier
            
        Returns:
            True si l'archive est intègre
        """
        archive_path = Path(archive_path)
        control_file = archive_path.with_suffix(".sha256")
        
        if not control_file.exists():
            logger.error("Fichier de contrôle non trouvé")
            return False
        
        # Lire le hash attendu
        expected_hash = control_file.read_text().split()[0]
        
        # Calculer le hash actuel
        current_hash = self._compute_hash(archive_path)
        
        is_valid = expected_hash == current_hash
        
        if is_valid:
            logger.info("✓ Archive intègre")
        else:
            logger.error("✗ Archive corrompue ou modifiée")
        
        return is_valid
    
    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        """Calcule le hash SHA256 d'un fichier."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


# Fonction utilitaire
def archive_documents(
    files: List[Path],
    output_dir: Path,
    period: str = None,
) -> Path:
    """
    Archive une liste de documents.
    
    Args:
        files: Fichiers à archiver
        output_dir: Dossier de destination
        period: Période (ex: "2024-12")
        
    Returns:
        Chemin de l'archive
    """
    archiver = ArchiveurLegal(output_dir)
    return archiver.create_archive(files, period=period)
