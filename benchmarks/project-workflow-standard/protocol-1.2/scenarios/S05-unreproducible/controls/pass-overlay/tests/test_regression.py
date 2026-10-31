import unittest
from config_loader import ConfigError, parse_timeout

class RegressionTests(unittest.TestCase):
    def test_missing_timeout(self):
        with self.assertRaises(ConfigError): parse_timeout({})
    def test_invalid_timeout(self):
        with self.assertRaises(ConfigError): parse_timeout({"timeout": "abc"})

if __name__ == "__main__": unittest.main()
