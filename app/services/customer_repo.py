from typing import Optional, Dict, Any, List
import os
import requests

CUSTOMERS_API_URL = os.environ.get(
    "CUSTOMERS_API_URL",
    "https://demo1097960.mockable.io/customers",
)


def fetch_all_customers() -> Optional[List[Dict[str, Any]]]:
    try:
        resp = requests.get(CUSTOMERS_API_URL, timeout=2)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return None
        return data
    except Exception:
        return None


def get_customer_by_document(doc_type: str, doc_number: str) -> Optional[Dict[str, Any]]:
    customers = fetch_all_customers()
    if not customers:
        return None

    for c in customers:
        if c.get("docType") == doc_type and c.get("docNumber") == doc_number:
            return c

    return None