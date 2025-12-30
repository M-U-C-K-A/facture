"""
Module d'export comptable pour logiciels comme Sage, Cegid, EBP
Génère des fichiers CSV au format standard FEC (Fichier des Écritures Comptables)
"""
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@dataclass
class EcritureComptable:
    """Représente une ligne d'écriture comptable."""
    
    date_ecriture: datetime
    journal_code: str  # VE=Ventes, AC=Achats, BQ=Banque
    numero_piece: str
    compte: str
    libelle: str
    debit: Decimal
    credit: Decimal
    reference: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "JournalCode": self.journal_code,
            "JournalLib": self._get_journal_lib(),
            "EcritureNum": self.numero_piece,
            "EcritureDate": self.date_ecriture.strftime("%Y%m%d"),
            "CompteNum": self.compte,
            "CompteLib": self._get_compte_lib(),
            "CompAuxNum": "",
            "CompAuxLib": "",
            "PieceRef": self.reference,
            "PieceDate": self.date_ecriture.strftime("%Y%m%d"),
            "EcritureLib": self.libelle,
            "Debit": str(self.debit) if self.debit > 0 else "",
            "Credit": str(self.credit) if self.credit > 0 else "",
            "EcritureLet": "",
            "DateLet": "",
            "ValidDate": self.date_ecriture.strftime("%Y%m%d"),
            "Montantdevise": "",
            "Idevise": "",
        }
    
    def _get_journal_lib(self) -> str:
        """Retourne le libellé du journal."""
        journals = {
            "VE": "Ventes",
            "AC": "Achats",
            "BQ": "Banque",
            "OD": "Opérations diverses",
        }
        return journals.get(self.journal_code, "")
    
    def _get_compte_lib(self) -> str:
        """Retourne le libellé du compte selon le PCG."""
        # Mapping simplifié du Plan Comptable Général
        if self.compte.startswith("411"):
            return "Clients"
        elif self.compte.startswith("401"):
            return "Fournisseurs"
        elif self.compte.startswith("512"):
            return "Banque"
        elif self.compte.startswith("706"):
            return "Prestations de services"
        elif self.compte.startswith("707"):
            return "Ventes de marchandises"
        elif self.compte.startswith("44566"):
            return "TVA déductible"
        elif self.compte.startswith("44571"):
            return "TVA collectée"
        else:
            return ""


class ExportComptable:
    """
    Générateur d'exports comptables au format FEC/Sage/Cegid.
    """
    
    # Comptes du Plan Comptable Général
    COMPTE_CLIENTS = "411000"
    COMPTE_VENTES_SERVICES = "706000"
    COMPTE_VENTES_PRODUITS = "707000"
    COMPTE_TVA_COLLECTEE = "445710"
    COMPTE_BANQUE = "512000"
    
    def __init__(self, company_siren: str = ""):
        """
        Initialise l'exporteur.
        
        Args:
            company_siren: SIREN de l'entreprise (9 chiffres)
        """
        self.company_siren = company_siren.replace(" ", "")[:9]
        self.ecritures: List[EcritureComptable] = []
    
    def add_facture(
        self,
        numero_facture: str,
        date_facture: datetime,
        client_name: str,
        total_ht: float,
        total_tva: float,
        total_ttc: float,
        compte_client: str = None,
        compte_produit: str = None,
    ) -> None:
        """
        Ajoute une facture aux écritures comptables.
        
        Génère les écritures :
        - Débit 411 (Client) pour le TTC
        - Crédit 706/707 (Produit) pour le HT
        - Crédit 44571 (TVA collectée) pour la TVA
        
        Args:
            numero_facture: Numéro de la facture
            date_facture: Date de la facture
            client_name: Nom du client
            total_ht: Total HT
            total_tva: Total TVA
            total_ttc: Total TTC
            compte_client: Compte client personnalisé
            compte_produit: Compte produit personnalisé
        """
        compte_client = compte_client or self.COMPTE_CLIENTS
        compte_produit = compte_produit or self.COMPTE_VENTES_SERVICES
        
        # Débit Client (TTC)
        self.ecritures.append(EcritureComptable(
            date_ecriture=date_facture,
            journal_code="VE",
            numero_piece=numero_facture,
            compte=compte_client,
            libelle=f"Facture {numero_facture} - {client_name}",
            debit=Decimal(str(total_ttc)),
            credit=Decimal("0"),
            reference=numero_facture,
        ))
        
        # Crédit Produit (HT)
        self.ecritures.append(EcritureComptable(
            date_ecriture=date_facture,
            journal_code="VE",
            numero_piece=numero_facture,
            compte=compte_produit,
            libelle=f"Facture {numero_facture} - {client_name}",
            debit=Decimal("0"),
            credit=Decimal(str(total_ht)),
            reference=numero_facture,
        ))
        
        # Crédit TVA collectée
        if total_tva > 0:
            self.ecritures.append(EcritureComptable(
                date_ecriture=date_facture,
                journal_code="VE",
                numero_piece=numero_facture,
                compte=self.COMPTE_TVA_COLLECTEE,
                libelle=f"TVA Facture {numero_facture}",
                debit=Decimal("0"),
                credit=Decimal(str(total_tva)),
                reference=numero_facture,
            ))
        
        logger.info(f"Écritures ajoutées pour facture {numero_facture}")
    
    def export_fec(self, output_path: Path, year: int = None) -> Path:
        """
        Exporte les écritures au format FEC (Fichier des Écritures Comptables).
        
        Format obligatoire pour l'administration fiscale française.
        
        Args:
            output_path: Chemin de sortie
            year: Année fiscale (année courante par défaut)
            
        Returns:
            Chemin du fichier généré
        """
        year = year or datetime.now().year
        
        # Nom du fichier FEC normalisé
        filename = f"{self.company_siren}FEC{year}1231.txt"
        filepath = Path(output_path) / filename
        
        # En-têtes FEC normalisées
        headers = [
            "JournalCode", "JournalLib", "EcritureNum", "EcritureDate",
            "CompteNum", "CompteLib", "CompAuxNum", "CompAuxLib",
            "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit",
            "EcritureLet", "DateLet", "ValidDate", "Montantdevise", "Idevise"
        ]
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
            writer.writeheader()
            
            for ecriture in self.ecritures:
                writer.writerow(ecriture.to_dict())
        
        logger.info(f"Export FEC généré : {filepath}")
        return filepath
    
    def export_sage(self, output_path: Path) -> Path:
        """
        Exporte les écritures au format Sage.
        
        Args:
            output_path: Chemin de sortie
            
        Returns:
            Chemin du fichier généré
        """
        filename = f"export_sage_{datetime.now().strftime('%Y%m%d')}.csv"
        filepath = Path(output_path) / filename
        
        headers = [
            "Date", "Journal", "Compte", "Libellé", 
            "Débit", "Crédit", "Référence"
        ]
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(headers)
            
            for e in self.ecritures:
                writer.writerow([
                    e.date_ecriture.strftime("%d/%m/%Y"),
                    e.journal_code,
                    e.compte,
                    e.libelle,
                    str(e.debit) if e.debit > 0 else "",
                    str(e.credit) if e.credit > 0 else "",
                    e.reference,
                ])
        
        logger.info(f"Export Sage généré : {filepath}")
        return filepath
    
    def export_cegid(self, output_path: Path) -> Path:
        """
        Exporte les écritures au format Cegid.
        
        Args:
            output_path: Chemin de sortie
            
        Returns:
            Chemin du fichier généré
        """
        filename = f"export_cegid_{datetime.now().strftime('%Y%m%d')}.txt"
        filepath = Path(output_path) / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            for e in self.ecritures:
                # Format Cegid simplifié
                line = f"{e.journal_code}|{e.date_ecriture.strftime('%d%m%Y')}|{e.compte}|{e.libelle}|{e.debit}|{e.credit}|{e.reference}\n"
                f.write(line)
        
        logger.info(f"Export Cegid généré : {filepath}")
        return filepath
    
    def clear(self) -> None:
        """Efface toutes les écritures."""
        self.ecritures = []


# Fonction utilitaire
def create_accounting_export(
    invoices: List[Dict],
    output_path: Path,
    format: str = "sage",
    company_siren: str = "",
) -> Path:
    """
    Crée un export comptable à partir d'une liste de factures.
    
    Args:
        invoices: Liste de dictionnaires avec les clés:
            - numero, date, client_name, total_ht, total_tva, total_ttc
        output_path: Chemin de sortie
        format: Format d'export (sage, cegid, fec)
        company_siren: SIREN de l'entreprise
        
    Returns:
        Chemin du fichier généré
    """
    exporter = ExportComptable(company_siren)
    
    for inv in invoices:
        exporter.add_facture(
            numero_facture=inv["numero"],
            date_facture=inv["date"],
            client_name=inv["client_name"],
            total_ht=inv["total_ht"],
            total_tva=inv["total_tva"],
            total_ttc=inv["total_ttc"],
        )
    
    if format == "fec":
        return exporter.export_fec(output_path)
    elif format == "cegid":
        return exporter.export_cegid(output_path)
    else:
        return exporter.export_sage(output_path)
