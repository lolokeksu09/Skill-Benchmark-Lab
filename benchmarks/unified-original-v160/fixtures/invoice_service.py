"""Intentionally vulnerable baseline for U160-06; not production code.

The candidate agent receives only this file plus the public task statement.
The evaluator's tests must remain outside the candidate's writable workspace.
"""
def get_invoice(rows, authenticated_tenant, invoice_id):
    """Return an invoice summary or None. ID lookup currently ignores tenant."""
    for row in rows:
        if row["id"] == invoice_id:
            return {"id":row["id"],"amount_cents":row["amount_cents"]}
    return None
