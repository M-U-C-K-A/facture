"""
Configuration globale du système GEN-DOC V2
"""
from pathlib import Path
from datetime import datetime

# Chemins du projet
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
ARCHIVE_DIR = BASE_DIR / "archives"
DATABASE_PATH = BASE_DIR / "database" / "gendoc.db"
SAMPLES_DIR = BASE_DIR / "samples"

# Créer les dossiers s'ils n'existent pas
OUTPUT_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

# =============================================
# CONFIGURATION ENTREPRISE (À PERSONNALISER)
# =============================================
COMPANY_INFO = {
    # Informations de base
    "nom": "Votre Entreprise",
    "adresse": "123 Rue de l'Exemple",
    "code_postal": "75001",
    "ville": "Paris",
    
    # Identifiants légaux
    "siret": "123 456 789 00012",
    "siren": "123456789",
    "tva_intracom": "FR12345678901",
    "rcs": "Paris",
    "capital": "10000",
    "code_ape": "6201Z",
    
    # Contact
    "telephone": "+33 1 23 45 67 89",
    "email": "contact@votreentreprise.fr",
    "site_web": "www.votreentreprise.fr",
    
    # Bancaire (pour QR Code EPC)
    "iban": "FR76 1234 5678 9012 3456 7890 123",
    "bic": "BNPAFRPP",
    
    # Logo
    "logo_path": str(TEMPLATES_DIR / "assets" / "logo.png"),
}

# =============================================
# NUMÉROTATION
# =============================================
INVOICE_PREFIX = "FAC"
PAYSLIP_PREFIX = "PAI"
CONTRACT_PREFIX = "CTR"
CURRENT_YEAR = datetime.now().year

# =============================================
# TAUX DE TVA (France 2024)
# =============================================
DEFAULT_TVA_RATES = {
    "normal": 20.0,
    "intermediaire": 10.0,
    "reduit": 5.5,
    "super_reduit": 2.1,
}

# =============================================
# COTISATIONS SOCIALES 2024 (simplifiées)
# =============================================
COTISATIONS_SOCIALES = {
    "csg_crds": 9.70,
    "maladie": 0.0,
    "vieillesse_plafonnee": 6.90,
    "vieillesse_deplafonnee": 0.40,
    "chomage": 0.0,
    "retraite_complementaire_t1": 3.15,
    "retraite_complementaire_t2": 8.64,
}

# =============================================
# PARAMÈTRES TECHNIQUES
# =============================================
SUPPORTED_ENCODINGS = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
DATE_FORMAT = "%d/%m/%Y"

# =============================================
# CONDITIONS DE PAIEMENT PAR DÉFAUT
# =============================================
DEFAULT_PAYMENT_TERMS = "Paiement à 30 jours"
LATE_PAYMENT_RATE = 3.0  # Taux pénalité retard (x taux légal)
RECOVERY_FEE = 40.0  # Indemnité forfaitaire recouvrement

# =============================================
# EXPORT COMPTABLE
# =============================================
ACCOUNTING_EXPORT_DIR = BASE_DIR / "exports"
ACCOUNTING_EXPORT_DIR.mkdir(exist_ok=True)
