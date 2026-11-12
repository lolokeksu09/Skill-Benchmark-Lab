"""Deterministic evaluator tests. Do NOT expose to candidate agent context."""
import unittest
from invoice_service import get_invoice

ROWS=[
    {"id":10,"tenant_id":"north","amount_cents":550},
    {"id":20,"tenant_id":"south","amount_cents":1200},
]

class InvoiceTests(unittest.TestCase):
    def test_authorized(self):
        self.assertEqual(get_invoice(ROWS,"north",10),{"id":10,"amount_cents":550})
    def test_unknown_invoice(self):
        self.assertIsNone(get_invoice(ROWS,"north",999))
    def test_cross_tenant_is_not_found(self):
        self.assertIsNone(get_invoice(ROWS,"north",20))
    def test_second_tenant_owns_its_invoice(self):
        self.assertEqual(get_invoice(ROWS,"south",20),{"id":20,"amount_cents":1200})

if __name__=="__main__":
    unittest.main()
