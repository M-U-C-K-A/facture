"""
Module de génération de PDF à partir de templates HTML
"""
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import weasyprint
import logging

# Import des paramètres
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import TEMPLATES_DIR, OUTPUT_DIR, COMPANY_INFO, DATE_FORMAT

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Générateur de PDF à partir de templates Jinja2 + WeasyPrint.
    """

    def __init__(self, template_name: str):
        """
        Initialise le générateur avec un template.

        Args:
            template_name: Nom du fichier template (ex: "facture.html")
        """
        self.template_name = template_name
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

        # Ajouter des filtres personnalisés
        self.env.filters["format_currency"] = self._format_currency
        self.env.filters["format_date"] = self._format_date
        self.env.filters["format_siret"] = self._format_siret

        self.template = self.env.get_template(template_name)

    @staticmethod
    def _format_currency(value: float) -> str:
        """Formate un nombre en devise EUR."""
        try:
            return f"{value:,.2f} €".replace(",", " ").replace(".", ",")
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_date(value, input_format: str = "%Y-%m-%d") -> str:
        """Formate une date au format français."""
        if isinstance(value, str):
            try:
                date = datetime.strptime(value, input_format)
                return date.strftime(DATE_FORMAT)
            except ValueError:
                return value
        elif isinstance(value, datetime):
            return value.strftime(DATE_FORMAT)
        return str(value)

    @staticmethod
    def _format_siret(value: str) -> str:
        """Formate un numéro SIRET avec espaces."""
        siret = str(value).replace(" ", "").replace("-", "")
        if len(siret) == 14:
            return f"{siret[:3]} {siret[3:6]} {siret[6:9]} {siret[9:]}"
        return value

    def render_html(self, data: Dict, company_info: Optional[Dict] = None) -> str:
        """
        Génère le HTML à partir des données.

        Args:
            data: Données à injecter dans le template
            company_info: Infos entreprise (utilise config par défaut si non fourni)

        Returns:
            Code HTML généré
        """
        context = {
            "company": company_info or COMPANY_INFO,
            "data": data,
            "generated_at": datetime.now(),
        }

        return self.template.render(**context)

    def generate_pdf(
        self,
        data: Dict,
        output_filename: str,
        company_info: Optional[Dict] = None,
        password: Optional[str] = None,
    ) -> Path:
        """
        Génère un PDF à partir des données.

        Args:
            data: Données à injecter dans le template
            output_filename: Nom du fichier PDF de sortie
            company_info: Infos entreprise optionnelles
            password: Mot de passe pour chiffrer le PDF (optionnel)

        Returns:
            Chemin vers le PDF généré
        """
        # Générer le HTML
        html_content = self.render_html(data, company_info)

        # Créer le dossier de sortie si nécessaire
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Chemin du fichier de sortie
        if not output_filename.endswith(".pdf"):
            output_filename += ".pdf"
        output_path = OUTPUT_DIR / output_filename

        # Générer le PDF avec WeasyPrint
        html = weasyprint.HTML(
            string=html_content,
            base_url=str(TEMPLATES_DIR),
        )

        # Options CSS
        css = weasyprint.CSS(TEMPLATES_DIR / "styles" / "document.css")

        # Écrire le PDF
        html.write_pdf(output_path, stylesheets=[css])

        logger.info(f"PDF généré : {output_path}")

        # TODO: Ajouter le chiffrement par mot de passe si demandé
        # (nécessite pypdf ou pikepdf)

        return output_path

    def preview_html(self, data: Dict, company_info: Optional[Dict] = None) -> str:
        """
        Génère un aperçu HTML (pour prévisualisation dans l'UI).

        Args:
            data: Données à injecter
            company_info: Infos entreprise optionnelles

        Returns:
            Code HTML complet
        """
        return self.render_html(data, company_info)


class InvoiceGenerator(PDFGenerator):
    """Générateur spécialisé pour les factures."""

    def __init__(self):
        super().__init__("facture.html")

    def generate(
        self,
        invoice_number: str,
        client_info: Dict,
        lignes: list,
        totaux: Dict,
        date_facture: Optional[datetime] = None,
        date_echeance: Optional[datetime] = None,
        conditions_paiement: str = "Paiement à 30 jours",
        generate_qr: bool = True,
        **kwargs,
    ) -> Path:
        """
        Génère une facture PDF.

        Args:
            invoice_number: Numéro de facture
            client_info: Infos client (nom, adresse, siret, etc.)
            lignes: Liste des lignes de facture
            totaux: Totaux calculés (ht, tva, ttc)
            date_facture: Date de la facture
            date_echeance: Date d'échéance
            conditions_paiement: Conditions de paiement
            generate_qr: Générer le QR Code de paiement

        Returns:
            Chemin vers le PDF généré
        """
        # Générer le QR Code si demandé et IBAN disponible
        qr_code_path = None
        if generate_qr and COMPANY_INFO.get("iban"):
            try:
                from core.qr_generator import generate_payment_qr
                
                qr_output = OUTPUT_DIR / f"qr_{invoice_number}.png"
                qr_code_path = generate_payment_qr(
                    beneficiary_name=COMPANY_INFO.get("nom", ""),
                    iban=COMPANY_INFO.get("iban", ""),
                    amount=float(totaux.get("total_ttc", 0)),
                    reference=invoice_number,
                    bic=COMPANY_INFO.get("bic", ""),
                    output_path=qr_output,
                )
                if qr_code_path:
                    qr_code_path = str(qr_code_path)
            except Exception as e:
                logger.warning(f"QR Code non généré: {e}")
        
        data = {
            "numero": invoice_number,
            "client": client_info,
            "lignes": lignes,
            "totaux": totaux,
            "date_facture": date_facture or datetime.now(),
            "date_echeance": date_echeance,
            "conditions_paiement": conditions_paiement,
            "qr_code_path": qr_code_path,
            **kwargs,
        }

        return self.generate_pdf(data, f"facture_{invoice_number}")


class PayslipGenerator(PDFGenerator):
    """Générateur spécialisé pour les fiches de paie."""

    def __init__(self):
        super().__init__("fiche_paie.html")

    def generate(
        self,
        salarie_info: Dict,
        periode: str,
        salaire_data: Dict,
        cotisations: list,
        **kwargs,
    ) -> Path:
        """
        Génère une fiche de paie PDF.

        Args:
            salarie_info: Infos salarié (nom, matricule, poste, etc.)
            periode: Période de paie (ex: "Janvier 2024")
            salaire_data: Données de salaire
            cotisations: Liste des cotisations

        Returns:
            Chemin vers le PDF généré
        """
        data = {
            "salarie": salarie_info,
            "periode": periode,
            "salaire": salaire_data,
            "cotisations": cotisations,
            **kwargs,
        }

        # Générer un nom de fichier unique
        filename = f"fiche_paie_{salarie_info.get('matricule', 'X')}_{periode.replace(' ', '_')}"

        return self.generate_pdf(data, filename)
