import re


def parse_nutrients(string: str | None):
    try:
        assert string is not None
        input_string = re.sub(r"\s+", " ", string).strip()

        # Define the regex pattern to match the undesired parts
        pattern = r"[a-zA-Z0-9]+\s%|DV"

        # Remove all matches
        cleaned_string = re.sub(pattern, "", input_string)
        cleaned_string = re.sub(r"\s+", " ", cleaned_string).strip()
        formated_data = format_nutrients(cleaned_string)
        return formated_data
    except Exception as e:
        print(f"And error occured while parsing nutrients {str(e)}")
        return None


def format_nutrients(input_string: str):
    # Regex pattern to extract the fields
    pattern = re.compile(r"([a-zA-Z\-\(\)\s]+)\s(\d+\.?\d*)\s?(mg|g|mcg|kcal|kj|calories|%)?", re.IGNORECASE)

    # Parse the string
    matches = pattern.findall(input_string)

    # Process the input data
    parsed_data = {}

    for match in matches:
        # Extract nutrient name, value, and unit
        nutrient_name = match[0].strip().lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
        nutrient_value = float(match[1]) if match[1] else 0
        nutrient_unit = match[2].strip().lower() if match[2] else ""

        # Handle "energy" and "kj" case
        if "energy" in nutrient_name and nutrient_unit == "kj":
            nutrient_name = f"{nutrient_name}_{nutrient_unit}"
            nutrient_unit = ""  # Prevent appending the unit again

        if "calories" in nutrient_name:
            nutrient_name = "calories"

        if "total_fat" in nutrient_name:
            nutrient_name = "fat"
        # Append unit to nutrient_name if applicable
        if nutrient_unit and nutrient_name != "calories" and not nutrient_name.startswith("energy_kj"):
            nutrient_name = f"{nutrient_name}_{nutrient_unit}"

        # Handle medicinal nutrients and special cases
        if nutrient_name == "per":
            continue  # Skip "per" entries entirely

        # Add to parsed data
        parsed_data[nutrient_name] = nutrient_value

    return parsed_data
