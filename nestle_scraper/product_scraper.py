from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
import logging
import json


@dataclass
class ProductData:
    url: str
    brand: str
    size: Optional[str]
    name: Optional[str]
    description: Optional[str] = None
    ingredients: Optional[str] = None
    nutrition_facts: Optional[Dict] = None


class ProductScraper:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        self.products_data = []

    def scrape_product_page(self, url, brand):
        try:
            self.driver.get(url)
            self.logger.info(f"Scraping product page: {url}")

            name = self._safe_get_text(".product-title")
            ingredients = self._safe_get_text(".sub-ingredient")

        except Exception:
            return None

    def _safe_get_text(self, selector: str) -> Optional[str]:
        try:
            element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element.text.strip()
        except Exception:
            return None

    def extract_nutrition(self):
        try:
            nutrition_container = self.driver.find_element(By.CLASS_NAME, "nutrients-container")
            rows = nutrition_container.find_elements(By.CLASS_NAME, "coh-row-inner")

            nutrient_data = []
            for row in rows:
                # Extract the nutrient label
                label = row.find_element(By.CLASS_NAME, "label-column").text.strip()

                # Extract the amount and unit
                amount_elem = row.find_element(By.CLASS_NAME, "first-column")
                amount_value = (
                    amount_elem.find_element(By.CLASS_NAME, "amount-value").text.strip()
                    if amount_elem
                    else ""
                )
                unit = amount_elem.text.replace(amount_value, "").strip() if amount_value else ""

                # Extract the % DV
                percent_elem = row.find_element(By.CLASS_NAME, "second-column")
                percent_dv = (
                    percent_elem.find_element(By.CLASS_NAME, "nutrient-value").text.strip()
                    if percent_elem
                    else ""
                )

                # Append to list
                nutrient_data.append(
                    {"Nutrient": label, "Amount": f"{amount_value} {unit}".strip(), "% DV": percent_dv}
                )
            return nutrient_data

        except Exception as e:
            self.logger.error(f"Error processing nutrition row: {str(e)}")
