import pathlib, unittest
from playwright.sync_api import sync_playwright

PAGE = (pathlib.Path(__file__).parents[1] / 'index.html').as_uri()

class BrowserChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = sync_playwright().start()
        cls.browser = cls.p.chromium.launch(headless=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.p.stop()
    def setUp(self): self.page = self.browser.new_page(viewport={"width":375,"height":800})
    def tearDown(self): self.page.close()
    def test_mobile_and_interactions(self):
        self.page.goto(PAGE)
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 375)
        self.page.locator('#search').fill('лесника')
        self.assertEqual(self.page.locator('.card:visible').count(), 1)
        save = self.page.locator('.save').first
        self.assertTrue(save.get_attribute('aria-label'))
        save.click()
        self.assertEqual(save.get_attribute('aria-pressed'), 'true')
        self.page.locator('#theme').click()
        self.assertEqual(self.page.evaluate('localStorage.getItem("rifthub-theme")'), 'dark')
    def test_keyboard_and_load_more(self):
        self.page.goto(PAGE)
        button = self.page.locator('.like').first
        button.focus(); self.page.keyboard.press('Enter')
        self.assertIn('♥', button.inner_text())
        self.page.locator('#more').click()
        self.assertGreater(self.page.locator('.card').count(), 3)

if __name__ == '__main__': unittest.main()
