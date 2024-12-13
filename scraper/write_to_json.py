from datetime import datetime
from typing import Dict, List
import json
import os
from dataclasses import dataclass, asdict
from uuid import uuid4


@dataclass
class ProductData:
    id: str  # Unique identifier for Azure Search
    url: str
    name: str
    brand: str
    size: str
    ingredients: List[str]
    nutrients: Dict[str, float]
    last_updated: str
    search_terms: List[str]  # For better searchability


class ProductProcessor:
    def __init__(self, output_dir: str = "../data/products/"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def process_product(self, product_info: Dict) -> ProductData:
        """
        Convert raw product info from scraper into structured ProductData
        """
        # Generate search terms from product name and brand
        search_terms = self._generate_search_terms(product_info["name"], product_info["brand"])

        # Convert all nutrient values to floats with 0 as default
        nutrients = {
            name.lower().replace(" ", "_"): float(value) if value else value
            for name, value in product_info.get("nutrients", {}).items()
        }

        # Create product data object
        product_data = ProductData(
            id=str(uuid4()),  # Generate unique ID for Azure Search
            url=product_info["url"],
            name=product_info["name"],
            brand=product_info["brand"],
            size=product_info["size"],
            ingredients=[i.strip() for i in product_info["ingredients"]],
            nutrients=nutrients,
            last_updated=datetime.utcnow().isoformat(),
            search_terms=search_terms,
        )

        return product_data

    def save_product_json(self, product_data: ProductData) -> str:
        """
        Save product data as JSON file with standardized naming
        Returns the file path
        """
        # Create filename from brand and product name
        safe_name = f"{product_data.brand}_{product_data.name}".lower()
        safe_name = "".join(c if c.isalnum() else "_" for c in safe_name)
        filename = f"{safe_name}_{product_data.id}.json"

        filepath = os.path.join(self.output_dir, filename)

        # Convert to dictionary and save as JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(product_data), f, indent=2, ensure_ascii=False)

        return filepath

    def _generate_search_terms(self, name: str, brand: str) -> List[str]:
        """
        Generate search terms from product name and brand
        """
        search_terms = []

        # Add full name and brand
        search_terms.append(name.lower())
        search_terms.append(brand.lower())

        # Add name parts (excluding common words)
        stop_words = {"with", "and", "or", "the", "in", "on", "at", "to"}
        name_parts = [word.lower() for word in name.split() if word.lower() not in stop_words]
        search_terms.extend(name_parts)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(search_terms))


def process_scraped_product(product_info: Dict):
    processor = ProductProcessor()
    product_data = processor.process_product(product_info)
    filepath = processor.save_product_json(product_data)
    return filepath
