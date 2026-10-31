import unittest
from config_loader import ConfigError, parse_timeout


class BaselineTests(unittest.TestCase):
    def test_integer_timeout(self):
        self.assertEqual(parse_timeout({"timeout": 30}), 30)

    def test_non_positive_rejected(self):
        with self.assertRaises(ConfigError):
            parse_timeout({"timeout": 0})


if __name__ == "__main__":
    unittest.main()
