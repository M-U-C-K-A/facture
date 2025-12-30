"""
Module Core - Moteur de traitement GEN-DOC V2
"""
from .data_reader import DataReader
from .validators import DataValidator, DocumentType
from .calculators import CalculatorFacture, CalculatorPaie
from .pdf_generator import PDFGenerator, InvoiceGenerator, PayslipGenerator
from .qr_generator import EPCQRGenerator, generate_payment_qr
from .export_comptable import ExportComptable, create_accounting_export
from .archiver import ArchiveurLegal, archive_documents

__all__ = [
    "DataReader",
    "DataValidator",
    "DocumentType",
    "CalculatorFacture",
    "CalculatorPaie",
    "PDFGenerator",
    "InvoiceGenerator",
    "PayslipGenerator",
    "EPCQRGenerator",
    "generate_payment_qr",
    "ExportComptable",
    "create_accounting_export",
    "ArchiveurLegal",
    "archive_documents",
]
