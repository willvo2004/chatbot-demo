class SelectorPattern:
    def __init__(self, name, validation_element, selectors):
        self.name = name
        self.validation_element = validation_element
        self.selectors = selectors


class BrandPageStructureHandler:
    def __init__(self):
        # Define different page structure patterns
        # Main purpose to access where the products are listed
        self.patterns = {
            "standard": SelectorPattern(
                name="standard",
                validation_element=".view-id-product_listing",
                selectors={"products": ".views-field-title a", "recipes": "Recipes"},
            ),
            "nescafe": SelectorPattern(
                name="nescafe",
                validation_element=".nescafe",
                selectors={"products": ".product-title", "recipes": "Nescafe Recipes"},
            ),
            "haagen-dazs": SelectorPattern(
                name="haagen-dazs",
                validation_element=".haagen-dazs",
                selectors={"products": ".views-field-title a", "recipes": "Recipes"},
            ),
            "boost": SelectorPattern(
                name="boost",
                validation_element=".boost",
                selectors={"products": ".views-field-title a", "recipes": "Recipes"},
            ),
            "natures-bounty": SelectorPattern(
                name="natures-bounty",
                validation_element=".natures-bounty",
                selectors={"products": ".views-field-title a", "recipes": ""},
            ),
            "drumstick": SelectorPattern(
                name="drumstick",
                validation_element=".drumstick",
                selectors={
                    "product_url": ".product-title",
                    "product_title": ".product-drumstick .coh-heading",
                    "recipes": "",
                },
            ),
        }
