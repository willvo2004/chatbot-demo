from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver import Remote, ChromeOptions
from dataclasses import dataclass
from typing import List, Optional, Dict
from dotenv import load_dotenv
import re
import logging
import json
import os


@dataclass
class Nutrients:
    name: str
    amount: float
    unit: Optional[str]


@dataclass
class ProductData:
    url: str
    brand: str
    size: Optional[str]
    name: Optional[str]
    description: Optional[str] = None
    ingredients: Optional[str] = None
    nutrition_facts: Optional[list] = None


class ProductScraper:
    def __init__(self, driver: Remote, logger):
        self.driver = driver
        self.logger = logger
        self.products_data = []

    def scrape_product_page(self, url, brand):
        try:
            self.driver.get(url)
            self.logger.info(f"Scraping product page: {url}")

            name = self._safe_get_text(".product-title")
            size = self._safe_get_text(".product-size")
            description = self._safe_get_text(".product-description p")
            ingredients = self._safe_get_text(".coh-ce-50eb162d p")  # safe get is not working so yeah

            nutrition_facts = self.extract_nutrition()

            return ProductData(
                url=url,
                brand=brand,
                size=size,
                name=name,
                description=description,
                ingredients=ingredients,
                nutrition_facts=nutrition_facts,
            )

        except Exception:
            return None

    def _safe_get_text(self, selector: str) -> Optional[str]:
        try:
            element = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            return element.text.strip()
        except Exception:
            return None

    def extract_nutrition(self):
        # Nested function defintion
        def format_string(string: str) -> List[Nutrients]:
            # Remove white space and new line characters
            cleaned_text = re.sub(r"\s+", " ", string.strip())
            nutrient_pattern = re.compile(
                r"(?P<name>[A-Za-z ]+)\s+(?P<amount>\d+\.?\d*)\s*(?P<unit>\w+)?\s*(?:% DV\s*(?P<percent>\d+)%\s*)?"
            )

            # Structure nutrients
            nutrients = []
            for match in nutrient_pattern.finditer(cleaned_text):
                nutrients.append(
                    {
                        "name": match.group("name").strip(),
                        "amount": float(match.group("amount")),
                        "unit": match.group("unit") or "",
                    }
                )
            return nutrients

        try:
            nutrition_container = self.driver.find_element(By.CLASS_NAME, "nutrients-container")
            text = nutrition_container.get_attribute("innerText")
            if text:
                return format_string(text)

        except Exception as e:
            self.logger.error(f"Error processing nutrition row: {str(e)}")

    def save_to_json(self, filename: str):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump([product.__dict__ for product in self.products_data], f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving to JSON: {str(e)}")


if __name__ == "__main__":
    load_dotenv()
    AUTH = os.getenv("PROXY")
    SBR_CONNECTION_STRING = f"https://{AUTH}@brd.superproxy.io:9515"

    sbr_connection = ChromiumRemoteConnection(SBR_CONNECTION_STRING, "goog", "chrome")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    driver = Remote(sbr_connection, options=ChromeOptions())
    logger = logging.getLogger(__name__)
    scraper = ProductScraper(driver, logger)
    print(scraper.scrape_product_page("https://www.madewithnestle.ca/after-eight/after-eight", "After Eight"))
