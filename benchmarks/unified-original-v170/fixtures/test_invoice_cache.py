"""Public deterministic negative control; never represent as agent-generated output."""
import unittest
from invoice_cache import invoice_summary

class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.rows={('north',12):{'amount_cents':200},('south',12):{'amount_cents':900}}
        self.cache={}

    def test_same_tenant_hit(self):
        a=invoice_summary('north',12,self.rows,self.cache)
        b=invoice_summary('north',12,self.rows,self.cache)
        self.assertEqual(a,b)

    def test_independent_invoice(self):
        self.assertIsNone(invoice_summary('north',404,self.rows,self.cache))

    def test_cross_tenant_same_id_is_isolated(self):
        self.assertEqual(invoice_summary('north',12,self.rows,self.cache)['amount_cents'],200)
        self.assertEqual(invoice_summary('south',12,self.rows,self.cache)['amount_cents'],900)

if __name__=='__main__':unittest.main()
