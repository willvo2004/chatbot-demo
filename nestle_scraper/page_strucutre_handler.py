class SelectorPattern:
    def __init__(self, name, validation_element, selectors):
        self.name = name
        self.validation_element = validation_element
        self.selectors = selectors


class BrandPageStructureHandler:
    def __init__(self):
        # Define different page structure patterns
        self.patterns = {
            "standard": SelectorPattern(
                name="standard",
                validation_element=".views-element-container",
                selectors={"products": ".views-field-title a", "recipes": "Recipes"},
            ),
            "nescafe": SelectorPattern(
                name="nescafe",
                validation_element=".home-coffee",
                selectors={"products": ".product-title", "recipes": "Nescafe Recipes"},
            ),
            # "legacy": SelectorPattern(
            #     name="legacy",
            #     validation_element="#oldProductTemplate",
            #     selectors={
            #         "name": "#productName",
            #         "description": "#productDescription",
            #         "ingredients": "#ingredientsList",
            #         "nutrition": "#nutritionPanel",
            #         "images": "#productGallery img",
            #     },
            # ),
        }
