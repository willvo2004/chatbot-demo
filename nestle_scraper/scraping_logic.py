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
        return cleaned_string
    except Exception as e:
        print(f"And error occured while parsing nutrients {str(e)}")
        return None
