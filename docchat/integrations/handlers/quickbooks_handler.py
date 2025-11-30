"""
Handler para QuickBooks
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class QuickBooksHandler(BaseIntegrationHandler):
    """Handler para QuickBooks."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """
        Busca en QuickBooks.
        
        access_token debe ser: "realm_id|access_token"
        """
        # Parsear token
        if "|" in access_token:
            realm_id, token = access_token.split("|", 1)
        else:
            realm_id = getattr(self.config, 'quickbooks_realm_id', '')
            token = access_token
        
        if not realm_id:
            print("⚠️ Necesitás configurar QUICKBOOKS_REALM_ID o incluirla en el token como 'realm_id|token'")
            return []
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        base_url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}"
        documents = []
        
        try:
            # Buscar en customers
            customers_url = f"{base_url}/query"
            query_str = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{query}%' MAXRESULTS {max_results // 2}"
            params = {"minorversion": "65", "query": query_str}
            response = requests.get(customers_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                customers = data.get("QueryResponse", {}).get("Customer", [])
                for customer in customers:
                    content = f"Customer: {customer.get('DisplayName', '')}\nCompany: {customer.get('CompanyName', '')}\nEmail: {customer.get('PrimaryEmailAddr', {}).get('Address', '')}"
                    documents.append(Document(
                        page_content=content,
                        metadata={
                            "source": "quickbooks - Customer",
                            "customer_id": customer.get("Id", ""),
                            "integration": "quickbooks"
                        }
                    ))
            
            # Buscar en invoices
            invoices_query = f"SELECT * FROM Invoice WHERE DocNumber LIKE '%{query}%' MAXRESULTS {max_results // 2}"
            params = {"minorversion": "65", "query": invoices_query}
            response = requests.get(customers_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                invoices = data.get("QueryResponse", {}).get("Invoice", [])
                for invoice in invoices:
                    content = f"Invoice: {invoice.get('DocNumber', '')}\nCustomer: {invoice.get('CustomerRef', {}).get('name', '')}\nTotal: {invoice.get('TotalAmt', '')}\nDue Date: {invoice.get('DueDate', '')}"
                    documents.append(Document(
                        page_content=content,
                        metadata={
                            "source": "quickbooks - Invoice",
                            "invoice_id": invoice.get("Id", ""),
                            "integration": "quickbooks"
                        }
                    ))
        except Exception as e:
            print(f"Error buscando en QuickBooks: {e}")
        
        return documents[:max_results]


