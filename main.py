"""
GEN-DOC - Système Automatisé de Génération de Documents
Point d'entrée principal de l'application
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("gendoc.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("GEN-DOC")

# Imports des modules
from core.data_reader import DataReader, read_data_file
from core.validators import DataValidator, DocumentType, validate_data
from core.calculators import CalculatorFacture, CalculatorPaie
from core.pdf_generator import InvoiceGenerator, PayslipGenerator
from database.logs import get_next_invoice_number, get_next_payslip_number, log_document
from config.settings import COMPANY_INFO, OUTPUT_DIR


def generate_invoices(input_file: str, preview: bool = False) -> list[Path]:
    """
    Génère des factures à partir d'un fichier CSV/Excel.

    Args:
        input_file: Chemin vers le fichier de données
        preview: Si True, affiche uniquement un aperçu

    Returns:
        Liste des chemins vers les PDF générés
    """
    logger.info(f"Lecture du fichier : {input_file}")

    # Lire les données
    reader = DataReader(input_file)
    df = reader.read()

    # Valider les données
    is_valid, results = validate_data(df, DocumentType.FACTURE)
    if not is_valid:
        logger.error("Erreurs de validation détectées")
        for result in results:
            for error in result.errors:
                logger.error(f"  {error}")
        return []

    # Grouper par client
    grouped = df.groupby(
        ["client_nom", "client_adresse", "client_code_postal", "client_ville"]
    )

    generated_files = []
    generator = InvoiceGenerator()

    for (client_nom, client_adresse, cp, ville), group in grouped:
        # Obtenir le prochain numéro de facture
        invoice_number = get_next_invoice_number()

        # Préparer les infos client
        client_info = {
            "nom": client_nom,
            "adresse": client_adresse,
            "code_postal": cp,
            "ville": ville,
            "siret": group["client_siret"].iloc[0] if "client_siret" in group.columns else "",
            "email": group["client_email"].iloc[0] if "client_email" in group.columns else "",
        }

        # Calculer les totaux
        calculator = CalculatorFacture.from_dataframe(group)
        totaux = calculator.to_dict()

        if preview:
            logger.info(f"\n{'='*50}")
            logger.info(f"Facture {invoice_number} pour {client_nom}")
            logger.info(f"Total HT : {totaux['total_ht']:.2f} €")
            logger.info(f"Total TTC : {totaux['total_ttc']:.2f} €")
            logger.info(f"{'='*50}")
            continue

        # Générer le PDF
        pdf_path = generator.generate(
            invoice_number=invoice_number,
            client_info=client_info,
            lignes=totaux["lignes"],
            totaux=totaux,
            date_facture=datetime.now(),
        )

        # Enregistrer dans les logs
        log_document(
            document_type="facture",
            document_number=invoice_number,
            filename=str(pdf_path),
            client_name=client_nom,
            total_amount=totaux["total_ttc"],
            source_file=input_file,
        )

        generated_files.append(pdf_path)
        logger.info(f"✓ Facture générée : {pdf_path}")

    return generated_files


def generate_payslips(input_file: str, period: str = None, preview: bool = False) -> list[Path]:
    """
    Génère des fiches de paie à partir d'un fichier CSV/Excel.

    Args:
        input_file: Chemin vers le fichier de données
        period: Période de paie (ex: "Décembre 2024")
        preview: Si True, affiche uniquement un aperçu

    Returns:
        Liste des chemins vers les PDF générés
    """
    logger.info(f"Lecture du fichier : {input_file}")

    # Période par défaut
    if period is None:
        period = datetime.now().strftime("%B %Y").capitalize()

    # Lire les données
    reader = DataReader(input_file)
    df = reader.read()

    # Valider les données
    is_valid, results = validate_data(df, DocumentType.FICHE_PAIE)
    if not is_valid:
        logger.error("Erreurs de validation détectées")
        for result in results:
            for error in result.errors:
                logger.error(f"  {error}")
        return []

    generated_files = []
    generator = PayslipGenerator()

    for _, row in df.iterrows():
        salaire_brut = float(row["salaire_brut"])

        # Calculer les cotisations
        calculator = CalculatorPaie(
            salaire_brut=salaire_brut,
            heures_travaillees=float(row.get("heures_travaillees", 151.67)),
        )
        salaire_data = calculator.to_dict()

        # Infos salarié
        salarie_info = {
            "nom": row["salarie_nom"],
            "prenom": row["salarie_prenom"],
            "matricule": row.get("salarie_matricule", ""),
            "poste": row["poste"],
            "date_embauche": row.get("date_embauche", ""),
        }

        if preview:
            logger.info(f"\n{'='*50}")
            logger.info(f"Fiche de paie : {salarie_info['prenom']} {salarie_info['nom']}")
            logger.info(f"Salaire brut : {salaire_brut:.2f} €")
            logger.info(f"Net avant impôt : {salaire_data['salaire_net_avant_impot']:.2f} €")
            logger.info(f"{'='*50}")
            continue

        # Générer le PDF
        pdf_path = generator.generate(
            salarie_info=salarie_info,
            periode=period,
            salaire_data=salaire_data,
            cotisations=salaire_data["cotisations"],
        )

        # Enregistrer dans les logs
        payslip_number = get_next_payslip_number()
        log_document(
            document_type="fiche_paie",
            document_number=payslip_number,
            filename=str(pdf_path),
            client_name=f"{salarie_info['prenom']} {salarie_info['nom']}",
            total_amount=salaire_data["salaire_net_avant_impot"],
            source_file=input_file,
        )

        generated_files.append(pdf_path)
        logger.info(f"✓ Fiche de paie générée : {pdf_path}")

    return generated_files


def main():
    """Point d'entrée principal avec interface CLI."""
    parser = argparse.ArgumentParser(
        description="GEN-DOC - Générateur de documents officiels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :
  python main.py facture samples/factures_sample.csv
  python main.py paie samples/paie_sample.csv --period "Décembre 2024"
  python main.py facture fichier.xlsx --preview
        """,
    )

    parser.add_argument(
        "type",
        choices=["facture", "paie", "contrat", "gui"],
        help="Type de document à générer ou 'gui' pour l'interface graphique",
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        help="Fichier CSV ou Excel contenant les données",
    )

    parser.add_argument(
        "--preview",
        "-p",
        action="store_true",
        help="Aperçu des documents sans génération",
    )

    parser.add_argument(
        "--period",
        help="Période de paie (ex: 'Décembre 2024')",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="Dossier de sortie pour les PDF",
    )

    args = parser.parse_args()

    # Lancer l'interface graphique
    if args.type == "gui":
        logger.info("Lancement de l'interface graphique...")
        from gui.app import run_app
        run_app()
        return

    # Vérifier le fichier d'entrée
    if not args.input_file:
        parser.error("Le fichier d'entrée est requis pour ce type de document")

    input_path = Path(args.input_file)
    if not input_path.exists():
        logger.error(f"Fichier introuvable : {input_path}")
        sys.exit(1)

    # Générer les documents
    if args.type == "facture":
        files = generate_invoices(str(input_path), preview=args.preview)
    elif args.type == "paie":
        files = generate_payslips(str(input_path), period=args.period, preview=args.preview)
    else:
        logger.error(f"Type de document non implémenté : {args.type}")
        sys.exit(1)

    # Résumé
    if files:
        logger.info(f"\n✅ {len(files)} document(s) généré(s) dans {OUTPUT_DIR}")
    elif not args.preview:
        logger.warning("Aucun document généré")


if __name__ == "__main__":
    main()
