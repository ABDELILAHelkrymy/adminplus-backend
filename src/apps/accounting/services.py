"""
Accounting Export Service
=========================
Generates exports compatible with professional accounting software (Sage 100, etc.)
following the Moroccan Chart of Accounts (Plan Comptable Marocain).

Supported Export Formats:
- CSV (Sage 100 compatible)
- Excel (.xlsx)
- JSON (structured data)
- UBL (Universal Business Language XML)

Double-Entry Bookkeeping Logic:
-------------------------------
For a PURCHASE invoice (expense):
  - Row 1: Debit the Expense account (Class 6, e.g., 61251 for Electricity)
  - Row 2: Debit the VAT Recoverable account (34552)
  - Row 3: Credit the Supplier account (4411)

For a SALE invoice (revenue):
  - Row 1: Debit the Customer account (3421)
  - Row 2: Credit the Revenue account (Class 7, e.g., 7111 for Sales)
  - Row 3: Credit the VAT Collected account (44552)
"""

import csv
import io
import json
from decimal import Decimal
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom

from django.db.models import QuerySet

from apps.invoices.models import Invoice, Category
from apps.accounts.models import BusinessAccount

logger = logging.getLogger(__name__)


class AccountingExportService:
    """
    Service class to generate accounting export CSV files compatible with
    Sage 100 and other professional accounting software.
    
    Uses the Moroccan Chart of Accounts (Plan Comptable Marocain).
    """
    
    # =========================================================================
    # MOROCCAN CHART OF ACCOUNTS - ACCOUNT CODE MAPPING
    # =========================================================================
    # Plan Comptable Marocain - Classification
    # 
    # Class 1: Financing Accounts (Comptes de financement permanent)
    # Class 2: Fixed Assets (Comptes d'actif immobilisé)
    # Class 3: Current Assets (Comptes d'actif circulant hors trésorerie)
    # Class 4: Current Liabilities (Comptes de passif circulant hors trésorerie)
    # Class 5: Treasury (Comptes de trésorerie)
    # Class 6: Expenses (Comptes de charges)
    # Class 7: Revenue (Comptes de produits)
    # =========================================================================
    
    # Default expense accounts (Class 6) - Map category names to account codes
    EXPENSE_ACCOUNT_MAPPING = {
        # 611 - Purchases of goods
        'achats_marchandises': '6111',
        'purchases': '6111',
        'achats': '6111',
        
        # 612 - Purchases consumed materials and supplies
        'fournitures': '6121',
        'supplies': '6121',
        'matieres_premieres': '6121',
        'raw_materials': '6121',
        
        # 613/614 - Other external charges
        'loyer': '6131',
        'rent': '6131',
        'location': '6132',
        'leasing': '6132',
        'entretien': '6133',
        'maintenance': '6133',
        'assurance': '6134',
        'insurance': '6134',
        
        # 615 - Other external charges (continued)
        'honoraires': '6136',
        'professional_fees': '6136',
        'consulting': '6136',
        'publicite': '6144',
        'advertising': '6144',
        'marketing': '6144',
        'transport': '6142',
        'shipping': '6142',
        'deplacement': '6143',
        'travel': '6143',
        
        # 616 - Taxes and duties
        'taxes': '6161',
        'impots': '6161',
        
        # 617 - Personnel charges
        'salaires': '6171',
        'salaries': '6171',
        'wages': '6171',
        
        # 618 - Other charges
        'electricite': '61251',
        'electricity': '61251',
        'eau': '61252',
        'water': '61252',
        'telephone': '6145',
        'telecom': '6145',
        'internet': '6145',
        
        # 619 - General operating expenses
        'general': '6191',
        'autres': '6191',
        'other': '6191',
        'miscellaneous': '6191',
    }
    
    # Default revenue accounts (Class 7)
    REVENUE_ACCOUNT_MAPPING = {
        # 711 - Sales of goods
        'ventes_marchandises': '7111',
        'sales_goods': '7111',
        'ventes': '7111',
        'sales': '7111',
        
        # 712 - Sales of services
        'prestations': '7121',
        'services': '7121',
        'consulting_revenue': '7121',
        
        # 713 - Other income
        'autres_produits': '7181',
        'other_income': '7181',
        
        # 714 - Ancillary products
        'commissions': '7127',
        'commission_income': '7127',
    }
    
    # Standard VAT accounts (Moroccan)
    VAT_ACCOUNTS = {
        'recoverable': '34552',      # TVA Récupérable sur charges
        'recoverable_assets': '34551',  # TVA Récupérable sur immobilisations
        'collected': '44552',        # TVA Facturée
        'due': '44551',              # TVA Due
    }
    
    # Third-party accounts
    THIRD_PARTY_ACCOUNTS = {
        'suppliers': '4411',         # Fournisseurs
        'customers': '3421',         # Clients
        'suppliers_advance': '3411', # Avances fournisseurs
        'customers_advance': '4421', # Avances clients
    }
    
    # Journal codes
    JOURNAL_CODES = {
        'purchases': 'AC',    # Achats
        'sales': 'VE',        # Ventes
        'bank': 'BQ',         # Banque
        'cash': 'CA',         # Caisse
        'operations': 'OD',   # Opérations Diverses
    }
    
    def __init__(self, business_account: BusinessAccount):
        """
        Initialize the service with a business account.
        
        Args:
            business_account: The business account to export data for.
        """
        self.business_account = business_account
        self.custom_mappings = self._load_custom_mappings()
    
    def _load_custom_mappings(self) -> Dict[str, str]:
        """
        Load any custom category-to-account mappings defined by the business.
        This could be extended to load from database in the future.
        
        Returns:
            Dictionary of custom category mappings.
        """
        # Future enhancement: Load from AccountMapping model
        return {}
    
    def get_expense_account(self, category: Optional[Category]) -> str:
        """
        Get the expense account code for a given category.
        
        Args:
            category: The invoice category (can be None).
            
        Returns:
            The account code string (e.g., "61251" for electricity).
        """
        if not category:
            return '6191'  # Default: Other operating expenses
        
        category_key = category.name.lower().replace(' ', '_').replace('-', '_')
        
        # Check custom mappings first
        if category_key in self.custom_mappings:
            return self.custom_mappings[category_key]
        
        # Check standard mappings
        if category_key in self.EXPENSE_ACCOUNT_MAPPING:
            return self.EXPENSE_ACCOUNT_MAPPING[category_key]
        
        # Try partial matching
        for key, account in self.EXPENSE_ACCOUNT_MAPPING.items():
            if key in category_key or category_key in key:
                return account
        
        # Default expense account
        return '6191'
    
    def get_revenue_account(self, category: Optional[Category]) -> str:
        """
        Get the revenue account code for a given category.
        
        Args:
            category: The invoice category (can be None).
            
        Returns:
            The account code string (e.g., "7111" for sales).
        """
        if not category:
            return '7111'  # Default: Sales of goods
        
        category_key = category.name.lower().replace(' ', '_').replace('-', '_')
        
        # Check custom mappings first
        if category_key in self.custom_mappings:
            return self.custom_mappings[category_key]
        
        # Check standard mappings
        if category_key in self.REVENUE_ACCOUNT_MAPPING:
            return self.REVENUE_ACCOUNT_MAPPING[category_key]
        
        # Try partial matching
        for key, account in self.REVENUE_ACCOUNT_MAPPING.items():
            if key in category_key or category_key in key:
                return account
        
        # Default revenue account
        return '7111'
    
    def _format_date(self, d: date) -> str:
        """Format date for CSV export (DD/MM/YYYY - French standard)."""
        return d.strftime('%d/%m/%Y')
    
    def _format_amount(self, amount: Decimal) -> str:
        """Format decimal amount for CSV (2 decimal places, no thousands separator)."""
        return f"{abs(amount):.2f}"
    
    def _get_partner_code(self, invoice: Invoice) -> str:
        """
        Generate a partner auxiliary code for the invoice.
        Used to identify specific suppliers/customers in the accounting system.
        """
        if invoice.invoice_type == 'purchase' and invoice.supplier:
            # Use supplier number or generate from name
            if invoice.supplier.number:
                return f"F{invoice.supplier.number:05d}"
            return f"F{invoice.supplier.id.hex[:8].upper()}"
        elif invoice.customer:
            if invoice.customer.number:
                return f"C{invoice.customer.number:05d}"
            return f"C{invoice.customer.id.hex[:8].upper()}"
        return ""
    
    def _get_partner_name(self, invoice: Invoice) -> str:
        """Get the partner name for the invoice."""
        if invoice.invoice_type == 'purchase' and invoice.supplier:
            return invoice.supplier.corporate_name
        elif invoice.customer:
            return invoice.customer.corporate_name
        return "Unknown"
    
    def generate_purchase_entries(self, invoice: Invoice) -> List[Dict]:
        """
        Generate accounting entries for a purchase (expense) invoice.
        
        Double-entry for purchase:
        1. Debit: Expense account (HT amount)
        2. Debit: VAT Recoverable (TVA amount)
        3. Credit: Supplier account (TTC amount)
        
        Args:
            invoice: The purchase invoice.
            
        Returns:
            List of entry dictionaries.
        """
        entries = []
        journal = self.JOURNAL_CODES['purchases']
        date_str = self._format_date(invoice.date)
        piece = invoice.invoice_number or invoice.reference or str(invoice.id)[:8]
        partner_name = self._get_partner_name(invoice)
        partner_code = self._get_partner_code(invoice)
        
        # Row 1: Expense Account (Debit HT)
        expense_account = self.get_expense_account(invoice.category)
        entries.append({
            'journal': journal,
            'date': date_str,
            'piece': piece,
            'compte': expense_account,
            'auxiliaire': '',
            'libelle': f"{partner_name} - {invoice.about or 'Facture'}",
            'debit': self._format_amount(invoice.subtotal),
            'credit': '',
            'reference': invoice.reference or '',
        })
        
        # Row 2: VAT Recoverable (Debit TVA)
        if invoice.vat_amount and invoice.vat_amount > 0:
            entries.append({
                'journal': journal,
                'date': date_str,
                'piece': piece,
                'compte': self.VAT_ACCOUNTS['recoverable'],
                'auxiliaire': '',
                'libelle': f"TVA Récupérable - {partner_name}",
                'debit': self._format_amount(invoice.vat_amount),
                'credit': '',
                'reference': invoice.reference or '',
            })
        
        # Row 3: Supplier Account (Credit TTC)
        entries.append({
            'journal': journal,
            'date': date_str,
            'piece': piece,
            'compte': self.THIRD_PARTY_ACCOUNTS['suppliers'],
            'auxiliaire': partner_code,
            'libelle': f"{partner_name} - {invoice.invoice_number}",
            'debit': '',
            'credit': self._format_amount(invoice.total),
            'reference': invoice.reference or '',
        })
        
        return entries
    
    def generate_sale_entries(self, invoice: Invoice) -> List[Dict]:
        """
        Generate accounting entries for a sale (revenue) invoice.
        
        Double-entry for sale:
        1. Debit: Customer account (TTC amount)
        2. Credit: Revenue account (HT amount)
        3. Credit: VAT Collected (TVA amount)
        
        Args:
            invoice: The sale invoice.
            
        Returns:
            List of entry dictionaries.
        """
        entries = []
        journal = self.JOURNAL_CODES['sales']
        date_str = self._format_date(invoice.date)
        piece = invoice.invoice_number or str(invoice.id)[:8]
        partner_name = self._get_partner_name(invoice)
        partner_code = self._get_partner_code(invoice)
        
        # Row 1: Customer Account (Debit TTC)
        entries.append({
            'journal': journal,
            'date': date_str,
            'piece': piece,
            'compte': self.THIRD_PARTY_ACCOUNTS['customers'],
            'auxiliaire': partner_code,
            'libelle': f"{partner_name} - {invoice.invoice_number}",
            'debit': self._format_amount(invoice.total),
            'credit': '',
            'reference': invoice.reference or '',
        })
        
        # Row 2: Revenue Account (Credit HT)
        revenue_account = self.get_revenue_account(invoice.category)
        entries.append({
            'journal': journal,
            'date': date_str,
            'piece': piece,
            'compte': revenue_account,
            'auxiliaire': '',
            'libelle': f"{partner_name} - {invoice.about or 'Facture'}",
            'debit': '',
            'credit': self._format_amount(invoice.subtotal),
            'reference': invoice.reference or '',
        })
        
        # Row 3: VAT Collected (Credit TVA)
        if invoice.vat_amount and invoice.vat_amount > 0:
            entries.append({
                'journal': journal,
                'date': date_str,
                'piece': piece,
                'compte': self.VAT_ACCOUNTS['collected'],
                'auxiliaire': '',
                'libelle': f"TVA Collectée - {partner_name}",
                'debit': '',
                'credit': self._format_amount(invoice.vat_amount),
                'reference': invoice.reference or '',
            })
        
        return entries
    
    def get_invoices(
        self,
        start_date: date,
        end_date: date,
        journal_type: str
    ) -> QuerySet:
        """
        Get invoices for the export based on date range and journal type.
        
        Args:
            start_date: Start date of the period.
            end_date: End date of the period.
            journal_type: 'purchases', 'sales', or 'all'.
            
        Returns:
            QuerySet of Invoice objects.
        """
        queryset = Invoice.objects.filter(
            business_account=self.business_account,
            date__gte=start_date,
            date__lte=end_date,
        ).exclude(
            status='draft'  # Don't export draft invoices
        ).exclude(
            status='cancelled'  # Don't export cancelled invoices
        ).select_related(
            'supplier', 'customer', 'category'
        ).order_by('date', 'invoice_number')
        
        if journal_type == 'purchases':
            queryset = queryset.filter(invoice_type='purchase')
        elif journal_type == 'sales':
            queryset = queryset.filter(invoice_type__in=['sale', 'invoice'])
        # 'all' returns everything
        
        return queryset
    
    def generate_csv(
        self,
        start_date: date,
        end_date: date,
        journal_type: str = 'all',
        encoding: str = 'utf-8-sig'  # UTF-8 with BOM for Excel compatibility
    ) -> Tuple[str, str]:
        """
        Generate the complete CSV export file.
        
        Args:
            start_date: Start date of the period.
            end_date: End date of the period.
            journal_type: 'purchases', 'sales', or 'all'.
            encoding: Character encoding for the CSV file.
            
        Returns:
            Tuple of (csv_content, filename).
        """
        invoices = self.get_invoices(start_date, end_date, journal_type)
        
        all_entries = []
        
        for invoice in invoices:
            if invoice.invoice_type == 'purchase':
                entries = self.generate_purchase_entries(invoice)
            else:  # sale or invoice
                entries = self.generate_sale_entries(invoice)
            
            all_entries.extend(entries)
        
        # Generate CSV
        output = io.StringIO()
        
        # CSV Header - Sage 100 compatible format
        fieldnames = [
            'Journal',
            'Date',
            'Pièce',
            'Compte',
            'Auxiliaire',
            'Libellé',
            'Débit',
            'Crédit',
            'Référence',
        ]
        
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=';',  # Semicolon for European format
            quoting=csv.QUOTE_MINIMAL,
            extrasaction='ignore'
        )
        
        writer.writeheader()
        
        for entry in all_entries:
            writer.writerow({
                'Journal': entry['journal'],
                'Date': entry['date'],
                'Pièce': entry['piece'],
                'Compte': entry['compte'],
                'Auxiliaire': entry['auxiliaire'],
                'Libellé': entry['libelle'],
                'Débit': entry['debit'],
                'Crédit': entry['credit'],
                'Référence': entry['reference'],
            })
        
        csv_content = output.getvalue()
        output.close()
        
        # Generate filename
        business_name = self.business_account.business_name.replace(' ', '_')[:20]
        journal_name = journal_type.upper()
        date_range = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        filename = f"export_compta_{business_name}_{journal_name}_{date_range}.csv"
        
        logger.info(
            f"Generated accounting export: {filename} with {len(all_entries)} entries "
            f"from {len(invoices)} invoices"
        )
        
        return csv_content, filename
    
    def get_export_summary(
        self,
        start_date: date,
        end_date: date,
        journal_type: str = 'all'
    ) -> Dict:
        """
        Get a summary of what will be exported (for preview).
        
        Args:
            start_date: Start date of the period.
            end_date: End date of the period.
            journal_type: 'purchases', 'sales', or 'all'.
            
        Returns:
            Dictionary with export summary.
        """
        invoices = self.get_invoices(start_date, end_date, journal_type)
        
        purchase_count = invoices.filter(invoice_type='purchase').count()
        sale_count = invoices.filter(invoice_type__in=['sale', 'invoice']).count()
        
        from django.db.models import Sum
        
        totals = invoices.aggregate(
            total_ht=Sum('subtotal'),
            total_tva=Sum('vat_amount'),
            total_ttc=Sum('total'),
        )
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            },
            'journal_type': journal_type,
            'invoice_count': {
                'purchases': purchase_count,
                'sales': sale_count,
                'total': invoices.count(),
            },
            'totals': {
                'subtotal': float(totals['total_ht'] or 0),
                'vat': float(totals['total_tva'] or 0),
                'total': float(totals['total_ttc'] or 0),
            },
            'estimated_entries': (purchase_count * 3) + (sale_count * 3),
        }

    def generate_excel(
        self,
        start_date: date,
        end_date: date,
        journal_type: str = 'all'
    ) -> Tuple[bytes, str]:
        """
        Generate an Excel (.xlsx) export file.
        
        Args:
            start_date: Start date of the period.
            end_date: End date of the period.
            journal_type: 'purchases', 'sales', or 'all'.
            
        Returns:
            Tuple of (excel_content_bytes, filename).
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
            from openpyxl.utils import get_column_letter
        except ImportError:
            raise ImportError("openpyxl is required for Excel export. Install with: pip install openpyxl")
        
        invoices = self.get_invoices(start_date, end_date, journal_type)
        
        all_entries = []
        for invoice in invoices:
            if invoice.invoice_type == 'purchase':
                entries = self.generate_purchase_entries(invoice)
            else:
                entries = self.generate_sale_entries(invoice)
            all_entries.extend(entries)
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Écritures Comptables"
        
        # Header styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Headers
        headers = ['Journal', 'Date', 'Pièce', 'Compte', 'Auxiliaire', 'Libellé', 'Débit', 'Crédit', 'Référence']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Data rows
        for row_idx, entry in enumerate(all_entries, 2):
            ws.cell(row=row_idx, column=1, value=entry['journal']).border = thin_border
            ws.cell(row=row_idx, column=2, value=entry['date']).border = thin_border
            ws.cell(row=row_idx, column=3, value=entry['piece']).border = thin_border
            ws.cell(row=row_idx, column=4, value=entry['compte']).border = thin_border
            ws.cell(row=row_idx, column=5, value=entry['auxiliaire']).border = thin_border
            ws.cell(row=row_idx, column=6, value=entry['libelle']).border = thin_border
            
            # Debit/Credit as numbers
            debit_val = float(entry['debit']) if entry['debit'] else None
            credit_val = float(entry['credit']) if entry['credit'] else None
            debit_cell = ws.cell(row=row_idx, column=7, value=debit_val)
            credit_cell = ws.cell(row=row_idx, column=8, value=credit_val)
            debit_cell.border = thin_border
            credit_cell.border = thin_border
            debit_cell.number_format = '#,##0.00'
            credit_cell.number_format = '#,##0.00'
            
            ws.cell(row=row_idx, column=9, value=entry['reference']).border = thin_border
        
        # Auto-adjust column widths
        for col in range(1, 10):
            ws.column_dimensions[get_column_letter(col)].width = 15
        ws.column_dimensions['F'].width = 40  # Libellé column wider
        
        # Add summary sheet
        ws_summary = wb.create_sheet(title="Résumé")
        summary_data = [
            ["Export Comptable", ""],
            ["", ""],
            ["Période", f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"],
            ["Type de Journal", journal_type],
            ["Nombre de factures", len(invoices)],
            ["Nombre d'écritures", len(all_entries)],
            ["", ""],
            ["Entreprise", self.business_account.business_name],
        ]
        for row_idx, (label, value) in enumerate(summary_data, 1):
            ws_summary.cell(row=row_idx, column=1, value=label)
            ws_summary.cell(row=row_idx, column=2, value=value)
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        excel_content = output.getvalue()
        output.close()
        
        # Generate filename
        business_name = self.business_account.business_name.replace(' ', '_')[:20]
        journal_name = journal_type.upper()
        date_range = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        filename = f"export_compta_{business_name}_{journal_name}_{date_range}.xlsx"
        
        logger.info(f"Generated Excel export: {filename} with {len(all_entries)} entries")
        
        return excel_content, filename

    def generate_json(
        self,
        start_date: date,
        end_date: date,
        journal_type: str = 'all'
    ) -> Tuple[str, str]:
        """
        Generate a JSON export file with structured accounting data.
        
        Args:
            start_date: Start date of the period.
            end_date: End date of the period.
            journal_type: 'purchases', 'sales', or 'all'.
            
        Returns:
            Tuple of (json_content, filename).
        """
        invoices = self.get_invoices(start_date, end_date, journal_type)
        
        all_entries = []
        invoices_data = []
        
        for invoice in invoices:
            if invoice.invoice_type == 'purchase':
                entries = self.generate_purchase_entries(invoice)
            else:
                entries = self.generate_sale_entries(invoice)
            all_entries.extend(entries)
            
            # Build invoice data
            partner = invoice.supplier or invoice.customer
            partner_name = partner.corporate_name if partner else "Inconnu"
            
            invoices_data.append({
                'id': str(invoice.id),
                'type': invoice.invoice_type,
                'invoice_number': invoice.invoice_number,
                'date': invoice.date.isoformat(),
                'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
                'partner': {
                    'name': partner_name,
                    'code': getattr(partner, 'code', None),
                },
                'category': invoice.category.name if invoice.category else None,
                'amounts': {
                    'subtotal': float(invoice.subtotal or 0),
                    'vat_amount': float(invoice.vat_amount or 0),
                    'total': float(invoice.total or 0),
                    'vat_rate': float(invoice.vat_rate or 20),
                },
                'reference': invoice.reference,
                'status': invoice.status,
                'accounting_entries': entries,
            })
        
        export_data = {
            'export_info': {
                'format': 'comptago_accounting_export',
                'version': '1.0',
                'generated_at': datetime.now().isoformat(),
                'business': {
                    'name': self.business_account.business_name,
                    'id': str(self.business_account.id),
                },
            },
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            },
            'journal_type': journal_type,
            'summary': {
                'invoice_count': len(invoices),
                'entry_count': len(all_entries),
                'purchases': len([i for i in invoices_data if i['type'] == 'purchase']),
                'sales': len([i for i in invoices_data if i['type'] in ['sale', 'invoice']]),
            },
            'chart_of_accounts': 'Plan Comptable Marocain (PCM)',
            'invoices': invoices_data,
            'accounting_entries': all_entries,
        }
        
        json_content = json.dumps(export_data, ensure_ascii=False, indent=2)
        
        # Generate filename
        business_name = self.business_account.business_name.replace(' ', '_')[:20]
        journal_name = journal_type.upper()
        date_range = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        filename = f"export_compta_{business_name}_{journal_name}_{date_range}.json"
        
        logger.info(f"Generated JSON export: {filename} with {len(all_entries)} entries")
        
        return json_content, filename

    def generate_ubl(
        self,
        start_date: date,
        end_date: date,
        journal_type: str = 'all'
    ) -> Tuple[str, str]:
        """
        Generate a UBL-like (Universal Business Language) XML export.
        
        This follows a simplified UBL-inspired format suitable for
        interoperability with various accounting systems.
        
        Args:
            start_date: Start date of the period.
            end_date: End date of the period.
            journal_type: 'purchases', 'sales', or 'all'.
            
        Returns:
            Tuple of (xml_content, filename).
        """
        invoices = self.get_invoices(start_date, end_date, journal_type)
        
        # Create root element
        root = ET.Element('AccountingExport')
        root.set('xmlns', 'urn:comptago:accounting:export:1.0')
        root.set('version', '1.0')
        
        # Export info
        export_info = ET.SubElement(root, 'ExportInfo')
        ET.SubElement(export_info, 'GeneratedAt').text = datetime.now().isoformat()
        ET.SubElement(export_info, 'ChartOfAccounts').text = 'Plan Comptable Marocain (PCM)'
        
        business_elem = ET.SubElement(export_info, 'Business')
        ET.SubElement(business_elem, 'Name').text = self.business_account.business_name
        ET.SubElement(business_elem, 'ID').text = str(self.business_account.id)
        
        # Period
        period_elem = ET.SubElement(root, 'Period')
        ET.SubElement(period_elem, 'StartDate').text = start_date.isoformat()
        ET.SubElement(period_elem, 'EndDate').text = end_date.isoformat()
        ET.SubElement(period_elem, 'JournalType').text = journal_type
        
        # Invoices
        invoices_elem = ET.SubElement(root, 'Invoices')
        
        for invoice in invoices:
            inv_elem = ET.SubElement(invoices_elem, 'Invoice')
            inv_elem.set('type', invoice.invoice_type)
            
            ET.SubElement(inv_elem, 'ID').text = str(invoice.id)
            ET.SubElement(inv_elem, 'InvoiceNumber').text = invoice.invoice_number or ''
            ET.SubElement(inv_elem, 'IssueDate').text = invoice.date.isoformat()
            if invoice.due_date:
                ET.SubElement(inv_elem, 'DueDate').text = invoice.due_date.isoformat()
            
            # Party (Supplier or Customer)
            partner = invoice.supplier or invoice.customer
            if partner:
                party_elem = ET.SubElement(inv_elem, 'Party')
                party_elem.set('role', 'supplier' if invoice.supplier else 'customer')
                ET.SubElement(party_elem, 'Name').text = partner.corporate_name or ''
                if hasattr(partner, 'ice') and partner.ice:
                    ET.SubElement(party_elem, 'TaxID').text = partner.ice
            
            # Monetary totals
            monetary_elem = ET.SubElement(inv_elem, 'LegalMonetaryTotal')
            ET.SubElement(monetary_elem, 'LineExtensionAmount').text = str(invoice.subtotal or 0)
            ET.SubElement(monetary_elem, 'TaxExclusiveAmount').text = str(invoice.subtotal or 0)
            ET.SubElement(monetary_elem, 'TaxAmount').text = str(invoice.vat_amount or 0)
            ET.SubElement(monetary_elem, 'PayableAmount').text = str(invoice.total or 0)
            
            # Tax info
            tax_elem = ET.SubElement(inv_elem, 'TaxTotal')
            ET.SubElement(tax_elem, 'TaxAmount').text = str(invoice.vat_amount or 0)
            tax_subtotal = ET.SubElement(tax_elem, 'TaxSubtotal')
            ET.SubElement(tax_subtotal, 'TaxableAmount').text = str(invoice.subtotal or 0)
            ET.SubElement(tax_subtotal, 'TaxAmount').text = str(invoice.vat_amount or 0)
            ET.SubElement(tax_subtotal, 'Percent').text = str(invoice.vat_rate or 20)
            
            # Accounting entries for this invoice
            if invoice.invoice_type == 'purchase':
                entries = self.generate_purchase_entries(invoice)
            else:
                entries = self.generate_sale_entries(invoice)
            
            entries_elem = ET.SubElement(inv_elem, 'AccountingEntries')
            for entry in entries:
                entry_elem = ET.SubElement(entries_elem, 'Entry')
                ET.SubElement(entry_elem, 'Journal').text = entry['journal']
                ET.SubElement(entry_elem, 'Date').text = entry['date']
                ET.SubElement(entry_elem, 'DocumentNumber').text = entry['piece']
                ET.SubElement(entry_elem, 'AccountCode').text = entry['compte']
                ET.SubElement(entry_elem, 'AuxiliaryCode').text = entry['auxiliaire']
                ET.SubElement(entry_elem, 'Description').text = entry['libelle']
                if entry['debit']:
                    ET.SubElement(entry_elem, 'DebitAmount').text = entry['debit']
                if entry['credit']:
                    ET.SubElement(entry_elem, 'CreditAmount').text = entry['credit']
        
        # Pretty print XML
        xml_string = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_string)
        xml_content = dom.toprettyxml(indent="  ", encoding=None)
        # Remove extra blank lines
        xml_content = '\n'.join([line for line in xml_content.split('\n') if line.strip()])
        
        # Generate filename
        business_name = self.business_account.business_name.replace(' ', '_')[:20]
        journal_name = journal_type.upper()
        date_range = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        filename = f"export_compta_{business_name}_{journal_name}_{date_range}.xml"
        
        logger.info(f"Generated UBL/XML export: {filename} with {len(invoices)} invoices")
        
        return xml_content, filename

    def generate_export(
        self,
        start_date: date,
        end_date: date,
        journal_type: str = 'all',
        format: str = 'csv'
    ) -> Tuple[any, str, str]:
        """
        Generate export in the specified format.
        
        Args:
            start_date: Start date of the period.
            end_date: End date of the period.
            journal_type: 'purchases', 'sales', or 'all'.
            format: Export format ('csv', 'excel', 'json', 'ubl').
            
        Returns:
            Tuple of (content, filename, content_type).
        """
        format = format.lower()
        
        if format == 'csv':
            content, filename = self.generate_csv(start_date, end_date, journal_type)
            content_type = 'text/csv; charset=utf-8-sig'
        elif format == 'excel' or format == 'xlsx':
            content, filename = self.generate_excel(start_date, end_date, journal_type)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif format == 'json':
            content, filename = self.generate_json(start_date, end_date, journal_type)
            content_type = 'application/json'
        elif format == 'ubl' or format == 'xml':
            content, filename = self.generate_ubl(start_date, end_date, journal_type)
            content_type = 'application/xml'
        else:
            raise ValueError(f"Unsupported export format: {format}. Supported: csv, excel, json, ubl")
        
        return content, filename, content_type
