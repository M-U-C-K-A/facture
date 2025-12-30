"""
Module de génération de QR Code EPC pour paiement SEPA
Format European Payments Council (EPC069-12)
"""
from pathlib import Path
from typing import Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Essayer d'importer qrcode
try:
    import qrcode
    from qrcode.image.pure import PyPNGImage
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    logger.warning("Module 'qrcode' non installé. QR Codes désactivés. Installez avec: pip install qrcode[pil]")


class EPCQRGenerator:
    """
    Générateur de QR Code au format EPC pour paiement SEPA.
    
    Le format EPC permet aux clients de scanner le QR code avec leur
    application bancaire pour payer instantanément.
    """
    
    # Format EPC (European Payments Council)
    SERVICE_TAG = "BCD"
    VERSION = "002"
    CHARACTER_SET = "1"  # UTF-8
    IDENTIFICATION = "SCT"  # SEPA Credit Transfer
    
    def __init__(
        self,
        beneficiary_name: str,
        iban: str,
        bic: str = "",
        currency: str = "EUR",
    ):
        """
        Initialise le générateur EPC QR.
        
        Args:
            beneficiary_name: Nom du bénéficiaire (max 70 caractères)
            iban: IBAN du bénéficiaire
            bic: BIC/SWIFT (optionnel depuis SEPA 2.0)
            currency: Code devise (EUR par défaut)
        """
        self.beneficiary_name = beneficiary_name[:70]
        self.iban = iban.replace(" ", "").upper()
        self.bic = bic.replace(" ", "").upper() if bic else ""
        self.currency = currency.upper()
    
    def generate(
        self,
        amount: float,
        reference: str = "",
        remittance_info: str = "",
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Génère un QR Code EPC pour un paiement.
        
        Args:
            amount: Montant à payer
            reference: Référence de paiement (numéro de facture)
            remittance_info: Information libre (max 140 caractères)
            output_path: Chemin de sortie pour l'image
            
        Returns:
            Chemin vers l'image générée ou None si erreur
        """
        if not QR_AVAILABLE:
            logger.error("QR Code non disponible - module qrcode non installé")
            return None
        
        # Formater le montant
        amount_str = f"{self.currency}{Decimal(str(amount)):.2f}"
        
        # Construire le payload EPC
        # Ligne par ligne selon la norme EPC069-12
        lines = [
            self.SERVICE_TAG,           # Service Tag
            self.VERSION,               # Version
            self.CHARACTER_SET,         # Character Set
            self.IDENTIFICATION,        # Identification Code
            self.bic,                   # BIC (peut être vide)
            self.beneficiary_name,      # Nom bénéficiaire
            self.iban,                  # IBAN
            amount_str,                 # Montant avec devise
            "",                         # Purpose Code (vide)
            reference[:35],             # Reference (max 35 car)
            remittance_info[:140],      # Remittance Info (max 140 car)
            "",                         # Beneficiary to originator info
        ]
        
        payload = "\n".join(lines)
        
        # Générer le QR Code
        qr = qrcode.QRCode(
            version=None,  # Auto-sizing
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        
        # Créer l'image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Chemin de sortie
        if output_path is None:
            output_path = Path(f"qr_payment_{reference}.png")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder
        img.save(str(output_path))
        logger.info(f"QR Code EPC généré : {output_path}")
        
        return output_path
    
    @staticmethod
    def is_available() -> bool:
        """Vérifie si la génération QR est disponible."""
        return QR_AVAILABLE


# Fonction utilitaire
def generate_payment_qr(
    beneficiary_name: str,
    iban: str,
    amount: float,
    reference: str,
    bic: str = "",
    output_path: Optional[Path] = None,
) -> Optional[Path]:
    """
    Génère un QR Code de paiement EPC.
    
    Args:
        beneficiary_name: Nom du bénéficiaire
        iban: IBAN du bénéficiaire  
        amount: Montant à payer
        reference: Référence (numéro de facture)
        bic: BIC/SWIFT (optionnel)
        output_path: Chemin de sortie
        
    Returns:
        Chemin vers l'image ou None
    """
    generator = EPCQRGenerator(
        beneficiary_name=beneficiary_name,
        iban=iban,
        bic=bic,
    )
    return generator.generate(
        amount=amount,
        reference=reference,
        output_path=output_path,
    )
