from selenium.webdriver.common.by import By
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from page_strucutre_handler import BrandPageStructureHandler
from load_content import load_products
from dotenv import load_dotenv
import logging
import os

load_dotenv()
AUTH = os.getenv("PROXY")
SBR_CONNECTION_STRING = f"https://{AUTH}@brd.superproxy.io:9515"


class Scraper:
    def __init__(self, url):
        sbr_connection = ChromiumRemoteConnection(SBR_CONNECTION_STRING, "goog", "chrome")
        self.url = url
        self.driver = Remote(sbr_connection, options=ChromeOptions())
        self.logging()

    def init_driver(self):
        self.logger.info("WebDriver init started")

    def logging(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

    def wait_for_element(self, by, value, timeout=10):
        try:
            element = WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((by, value)))
            return element
        except TimeoutException:
            self.logger.error(f"Timeout waiting for element: {value} ")
            return None

    def accept_cookies(self):
        self.logger.info("Accepting Cookies")

        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler"))
            )
            element.click()

        except Exception as e:
            self.logger.error(f"Error with cookie: {str(e)}")
            return None

    def select_brands(self):
        self.logger.info("Selecting brands")

        try:
            self.wait_for_element(By.CLASS_NAME, "brands-section")
            brand_atag = self.driver.find_elements(By.CSS_SELECTOR, ".brands-section .sitemap-sublist-item a")

            brands_list = []
            repeat_links = ["crunch", "mirage"]
            for link in brand_atag:
                href = link.get_attribute("href")
                if any(x in href for x in repeat_links):
                    continue

                brands_list.append(href)
            return brands_list
        except Exception as e:
            self.logger.error(f"Error with brands: {str(e)}")
            return None

    def scrape_brand_data(self, url):
        self.logger.info(f"Scraping brand page: {url}")
        brand_handler = BrandPageStructureHandler()

        try:
            self.driver.get(url)
            load_products(self.driver)
            for pattern_name, pattern in brand_handler.patterns.items():
                if self.driver.find_element(By.CSS_SELECTOR, pattern.validation_element):
                    product_grid = self.driver.find_elements(By.CSS_SELECTOR, pattern.selectors["products"])
                    product_links = [element.get_attribute("href") for element in product_grid]

        except Exception as e:
            self.logger.error(f"Error with brand {url}: {str(e)}")
            return None

    def scrape_product_page(self):
        return None

    def scrape_site(self):
        try:
            self.init_driver()
            self.driver.get(self.url)

            # Grab and scrape brand data
            brand_links = self.select_brands()
            print(brand_links)
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    scraper = Scraper("https://www.madewithnestle.ca/sitemap")
    scraper.scrape_site()
