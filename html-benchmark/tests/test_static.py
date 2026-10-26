import pathlib, re, unittest

PAGE = pathlib.Path(__file__).parents[1] / 'index.html'
TEXT = PAGE.read_text(encoding='utf-8')

class StaticChecks(unittest.TestCase):
    def test_single_file_has_no_external_dependencies(self):
        self.assertNotRegex(TEXT, r'<link[^>]+https?://|<script[^>]+src=|url\(https?://')
    def test_required_landmarks_and_controls_exist(self):
        for marker in ('<header', '<main', 'id="search"', 'id="filter"', 'id="theme"', 'id="more"', 'id="empty"'):
            self.assertIn(marker, TEXT)
    def test_save_and_accessibility_contract(self):
        self.assertRegex(TEXT, r'aria-pressed')
        self.assertRegex(TEXT, r'addEventListener\(["\']keydown')
    def test_safe_rendering_and_theme_persistence(self):
        self.assertNotRegex(TEXT, r'innerHTML\s*=')
        self.assertRegex(TEXT, r'localStorage')
    def test_no_fixed_mobile_width(self):
        self.assertNotRegex(TEXT, r'min-width\s*:\s*5')

if __name__ == '__main__': unittest.main()
