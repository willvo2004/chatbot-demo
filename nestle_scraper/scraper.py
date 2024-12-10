from selenium.webdriver.common.by import By
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from page_strucutre_handler import BrandPageStructureHandler
from load_content import load_products
from product_scraper import ProductScraper
from typing import Optional, Tuple
from dotenv import load_dotenv
import logging
import sys
import os

load_dotenv()
AUTH = os.getenv("PROXY")
SBR_CONNECTION_STRING = f"https://{AUTH}@brd.superproxy.io:9515"
SBR_CONNECTION = ChromiumRemoteConnection(SBR_CONNECTION_STRING, "goog", "chrome")


class Scraper:
    def __init__(self, url):
        self.url = url
        self.driver = None
        self.logging()

    def init_driver(self):
        self.driver = Remote(SBR_CONNECTION, options=ChromeOptions())
        self.logger.info("WebDriver init started")

    def logging(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

    def wait_for_element(self, by, value, timeout=10):
        assert self.driver is not None
        try:
            element = WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((by, value)))
            return element
        except TimeoutException:
            self.logger.error(f"Timeout waiting for element: {value} ")
            return None

    def select_brands(self) -> Optional[list[Tuple[str, str]]]:
        assert self.driver is not None
        self.logger.info("Collecting brand names and URLs")
        try:
            self.wait_for_element(By.CLASS_NAME, "brands-section")
            brand_items = self.driver.find_elements(By.CSS_SELECTOR, ".brands-section .sitemap-sublist-item a")

            brands_list = []
            # :(
            skip_links = ["crunch", "mirage", "purina", "maison perrier", "nestlebaby"]
            for link in brand_items:
                name = link.text.strip()
                href = link.get_attribute("href")

                # Assert to remove error hint
                assert href is not None
                if any(x in href for x in skip_links):
                    continue

                brands_list.append((name, href))
            return brands_list
        except Exception as e:
            self.logger.error(f"Error with brands: {str(e)}")
            return None

    # Invoked @ collect_brand_products()
    def select_brand_products(self, brand_name):
        assert self.driver is not None

        brand_handler = BrandPageStructureHandler()
        try:
            load_products(self.driver)
            self.logger.info(f"Opened {brand_name} page")

            product_links = []
            for pattern_name, pattern in brand_handler.patterns.items():
                if self.driver.find_element(By.CSS_SELECTOR, pattern.validation_element):
                    # Need to redo for different page structures
                    product_grid = self.driver.find_elements(By.CSS_SELECTOR, pattern.selectors["products"])
                    # Attach brand name to list of products
                    product_links = {brand_name: [element.get_attribute("href") for element in product_grid]}

            return product_links

        except Exception as e:
            self.logger.error(f"Error with brand {self.url}: {str(e)}")
            return None

    def collect_brands(self):
        try:
            self.init_driver()
            assert self.driver is not None

            self.driver.get(self.url)

            # Grab and scrape brands from sitemap
            brand_links = self.select_brands()
            return brand_links
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
            return None
        finally:
            self.driver.quit()

    def collect_brand_products(self, name):
        try:
            self.init_driver()
            assert self.driver is not None

            self.driver.get(self.url)
            product_links = self.select_brand_products(name)
            return product_links
        except Exception as e:
            self.logger.error(f"Error during scraping product: {str(e)}")
            return None
        finally:
            self.driver.quit()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Web scraping entry point
        scraper = Scraper("https://www.madewithnestle.ca/sitemap")

        # Collect all brand names and links
        brands = scraper.collect_brands()
        assert brands is not None

        for name, link in brands:
            scraper = Scraper(link)
            print(scraper.collect_brand_products(name))
    elif sys.argv[1] == "load_test":
        print("running load test")
        scraper = Scraper("https://www.madewithnestle.ca/aero#products")
        print(scraper.collect_brand_products("Aero"))
