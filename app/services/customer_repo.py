# app/services/customer_repo.py
from typing import Optional, Dict, Any, List
import os
import requests
import json

CUSTOMERS_API_URL = os.environ.get(
    "CUSTOMERS_API_URL",
    "https://demo1097960.mockable.io/customers",
)


def fetch_all_customers() -> Optional[List[Dict[str, Any]]]:
    print("➡️  Fetching customers from:", CUSTOMERS_API_URL)

    try:
        resp = requests.get(CUSTOMERS_API_URL, timeout=5)
        print(f"⬅️  Response status: {resp.status_code}")

        resp.raise_for_status()

        data = resp.json()

        print("⬅️  Raw response:", json.dumps(data, indent=2))

        if not isinstance(data, list):
            print("❌ ERROR: Response is not a list")
            return None

        print(f"✔️ Loaded {len(data)} customers")
        return data

    except Exception as e:
        print("❌ Exception while calling mock:", str(e))
        return None


def get_customer_by_document(doc_type: str, doc_number: str) -> Optional[Dict[str, Any]]:
    print(f"🔍 Searching for customer docType={doc_type}, docNumber={doc_number}")

    customers = fetch_all_customers()
    if not customers:
        print("❌ No customers loaded from mock")
        return None

    for c in customers:
        print(f"Comparing with: {c.get('docNumber')}")

        if (
            c.get("docType") == doc_type
            and str(c.get("docNumber")) == str(doc_number)
        ):
            print("✔️ Customer match found:", c)
            return c

    print("❌ No matching customer found")
    return None