from typing import Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from page_strucutre_handler import BrandPageStructureHandler
from load_content import load_products
from product_scraper import ProductScraper
from typing import Optional, Dict
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

    def select_brands(self) -> Optional[list[Tuple[str, str]]]:
        self.logger.info("Selecting brands")

        try:
            self.wait_for_element(By.CLASS_NAME, "brands-section")
            brand_items = self.driver.find_elements(
                By.CSS_SELECTOR, ".brands-section .sitemap-sublist-item a"
            )

            brands_list = []
            # :(
            skip_links = ["crunch", "mirage", "purina", "maison perrier", "nestlebaby"]
            for link in brand_items:
                name = link.text.strip()
                href = link.get_attribute("href")
                if any(x in href for x in skip_links):
                    continue

                brands_list.append((name, href))
            return brands_list
        except Exception as e:
            self.logger.error(f"Error with brands: {str(e)}")
            return None

    def scrape_brand_data(self, brand_obj: Tuple[str, str]):
        brand_name = brand_obj[0]
        url = brand_obj[1]

        self.logger.info(f"Scraping brand page: {url}")
        brand_handler = BrandPageStructureHandler()
        product_scraper = ProductScraper(self.driver, self.logger)
        try:
            self.driver.get(url)
            load_products(self.driver)
            for pattern_name, pattern in brand_handler.patterns.items():
                if self.driver.find_element(By.CSS_SELECTOR, pattern.validation_element):
                    # Need to redo for different page structures
                    product_grid = self.driver.find_elements(By.CSS_SELECTOR, pattern.selectors["products"])
                    product_links = [element.get_attribute("href") for element in product_grid]

                    # Scrape each product page
                    for link in product_links:
                        product_data = product_scraper.scrape_product_page(link, brand_name)
                        if product_data:
                            product_scraper.products_data.append(product_data)

            product_scraper.save_to_json(f"../data/{brand_name}_products.json")
        except Exception as e:
            self.logger.error(f"Error with brand {url}: {str(e)}")
            return None

    def scrape_site(self):
        try:
            self.init_driver()
            self.driver.get(self.url)

            # Grab and scrape brand data
            brand_links = self.select_brands()

            if brand_links:
                print(brand_links)
                for link in brand_links:
                    self.scrape_brand_data(link)
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    scraper = Scraper("https://www.madewithnestle.ca/sitemap")
    scraper.scrape_site()
