"""
Module Database - Gestion des logs et numérotation
"""
from .logs import DocumentLog, get_next_invoice_number, log_document

__all__ = ["DocumentLog", "get_next_invoice_number", "log_document"]
