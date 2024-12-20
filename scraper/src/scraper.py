from selenium.webdriver.common.by import By
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from page_strucutre_handler import BrandPageStructureHandler
from write_to_json import process_scraped_product
from load_content import load_products
from scraping_logic import parse_nutrients
from typing import Optional, Tuple
from dotenv import load_dotenv
import pprint
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
        try:
            assert self.driver is not None
            element = WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((by, value)))
            return element
        except TimeoutException:
            self.logger.error(f"Timeout waiting for element: {value} ")
            return None

    def select_brands(self) -> Optional[list[Tuple[str, str]]]:
        try:
            assert self.driver is not None
            self.logger.info("Collecting brand names and URLs")
            self.wait_for_element(By.CLASS_NAME, "brands-section")
            brand_items = self.driver.find_elements(By.CSS_SELECTOR, ".brands-section .sitemap-sublist-item a")

            brands_list = []
            # :(
            skip_links = ["crunch", "mirage", "purina", "sanpellegrino", "maisonperrier", "nestlebaby", "drumstick"]
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
    def select_brand_products(self, brand: str):
        brand_handler = BrandPageStructureHandler()
        try:
            assert self.driver is not None
            self.logger.info(f"Opened {brand} page")

            brand_products = {}
            for pattern_name, pattern in brand_handler.patterns.items():
                if pattern_name == "standard":
                    if self.wait_for_element(By.CSS_SELECTOR, pattern.validation_element, 2):
                        # Need to redo for different page structures
                        load_products(self.driver)
                        product_grid = self.driver.find_elements(By.CSS_SELECTOR, pattern.selectors["products"])
                        # Attach brand name to list of products
                        brand_products = [
                            {"name": element.text, "url": element.get_attribute("href")} for element in product_grid
                        ]
                elif pattern_name == "nescafe":
                    if self.wait_for_element(By.CSS_SELECTOR, pattern.validation_element, 2):
                        self.driver.quit()
                        self.init_driver()
                        self.driver.get("https://www.madewithnestle.ca/nescaf%C3%A9/coffee")
                        load_products(self.driver)
                        product_grid = self.driver.find_elements(By.CSS_SELECTOR, pattern.selectors["products"])
                        brand_products = [
                            {"name": element.text, "url": element.get_attribute("href")} for element in product_grid
                        ]
                elif pattern_name == "haagen-dazs":
                    if self.wait_for_element(By.CSS_SELECTOR, pattern.validation_element, 2):
                        # Work around for buggy behaviour
                        self.driver.quit()
                        self.init_driver()
                        self.driver.get("https://www.haagen-dazs.ca/en/hd-en/products")
                        load_products(self.driver)
                        product_grid = self.driver.find_elements(By.CSS_SELECTOR, pattern.selectors["products"])
                        brand_products = [
                            {"name": element.text, "url": element.get_attribute("href")} for element in product_grid
                        ]
                elif pattern_name == "boost":
                    if self.wait_for_element(By.CSS_SELECTOR, pattern.validation_element, 2):
                        self.driver.get("https://www.madewithnestle.ca/boost/products#products")
                        load_products(self.driver)
                        product_grid = self.driver.find_elements(By.CSS_SELECTOR, pattern.selectors["products"])
                        brand_products = [
                            {"name": element.text, "url": element.get_attribute("href")} for element in product_grid
                        ]
                elif pattern_name == "natures-bounty":
                    if self.wait_for_element(By.CSS_SELECTOR, pattern.validation_element, 2):
                        self.driver.get("https://www.madewithnestle.ca/natures-bounty/our-products")
                        load_products(self.driver)
                        product_grid = self.driver.find_elements(By.CSS_SELECTOR, pattern.selectors["products"])
                        brand_products = [
                            {"name": element.text, "url": element.get_attribute("href")} for element in product_grid
                        ]
            return brand_products

        except Exception as e:
            self.logger.error(f"Error with brand {self.url}: {str(e)}")
            return None

    def scrape_product_page(self, brand: str):
        try:
            assert self.driver is not None
            self.logger.info(f"Scraping product page: {url}")

            name = self._safe_get_text(".product-title")
            size = self._safe_get_text(".product-size")
            ingredients = self._safe_get_text(".sub-ingredients").split(",")
            nutrients = parse_nutrients(self._safe_get_text(".nutrients-container"))
            return {
                "url": url,  # KEY=true
                "name": name,
                "size": size,
                "brand": brand,
                "nutrients": nutrients,
                "ingredients": ingredients,
            }
        except Exception as e:
            self.logger.error(f"Something went wrong: {str(e)}")
            return None

    def _safe_get_text(self, selector: str) -> str:
        try:
            assert self.driver is not None
            element = (
                WebDriverWait(self.driver, 5)
                .until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                .get_attribute("innerText")
            )
            assert element is not None
            return element.strip()
        except Exception as e:
            self.logger.error(f"Error while locating element {selector}: {str(e)}")
            return ""

    # Main function evokers
    def collect_brands(self):
        try:
            self.init_driver()
            assert self.driver is not None

            self.driver.get(self.url)

            # Collect every brand from site map
            brand_links = self.select_brands()
            return brand_links
        except Exception as e:
            self.logger.error(f"Error while collecting brands: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

    def collect_brand_products(self, name: str):
        try:
            self.init_driver()
            assert self.driver is not None

            # Collect every product from a brand
            self.driver.get(self.url)
            brand_products = self.select_brand_products(name)
            return brand_products
        except Exception as e:
            self.logger.error(f"Error while collecting brand products: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

    def collect_product_info(self, brand: str):
        try:
            self.init_driver()
            assert self.driver is not None

            self.driver.get(self.url)
            product_info = self.scrape_product_page(brand)
            return product_info
        except Exception as e:
            self.logger.error(f"Error occured while collecting product information: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Web scraping entry point
        scraper = Scraper("https://www.madewithnestle.ca/sitemap")

        # Collect all brand names and links
        brands = scraper.collect_brands()
        assert brands is not None

        # Collect all products that belong to the brand
        brand_products = {}
        for brand_name, link in brands:
            scraper = Scraper(link)
            products = scraper.collect_brand_products(brand_name)
            brand_products[brand_name] = products

        # Scrape all products collected. Do not need to run every time.
        for brand, products in brand_products.items():
            for product in products:
                url = product["url"]
                scraper = Scraper(url)
                product_info = scraper.collect_product_info(brand)

                if product_info:
                    filepath = process_scraped_product(product_info)
                    print(f"Write file to {filepath}")
    # Various cmd line arguments to test features
    elif sys.argv[1] == "load_test":
        # Confirm product loader for standard layout
        scraper = Scraper("https://www.madewithnestle.ca/boost")
        print(scraper.collect_brand_products("Boost"))

    elif sys.argv[1] == "nescafe":
        scraper = Scraper("https://www.madewithnestle.ca/nescafe")
        scraper.collect_brand_products("nescafe")

    elif sys.argv[1] == "natures-bounty":
        scraper = Scraper("https://www.madewithnestle.ca/natures-bounty")
        scraper.collect_brand_products("natures-bounty")

    elif sys.argv[1] == "test_brand_products":
        # Test brand product data format
        sample_brands = [
            ("After Eight", "https://www.madewithnestle.ca/after-eight"),
            ("Mackintosh Toffee", "https://www.madewithnestle.ca/mackintosh-toffee"),
        ]
        brand_products = {}
        for name, link in sample_brands:
            scraper = Scraper(link)
            products = scraper.collect_brand_products(name)
            brand_products[name] = products
        print(brand_products)

    elif sys.argv[1] == "product_info":
        urls = [
            "https://www.madewithnestle.ca/boost/boost-plus-calories-chocolate",
        ]
        for url in urls:
            scraper = Scraper(url)
            product_info = scraper.collect_product_info("Boost")
            pprint.pp(product_info)
            if product_info:
                process_scraped_product(product_info)
