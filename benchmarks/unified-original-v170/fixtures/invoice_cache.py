"""Intentionally vulnerable cache fixture. Evaluator only; not production software."""
def invoice_summary(tenant_id, invoice_id, rows, cache):
    key=invoice_id  # BUG: cache key omits tenant identity.
    if key in cache:
        return cache[key]
    row=rows.get((tenant_id,invoice_id))
    result=None if row is None else {'id':invoice_id,'amount_cents':row['amount_cents']}
    cache[key]=result
    return result
