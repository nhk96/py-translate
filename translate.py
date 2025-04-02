import re
import sys
import json
from deep_translator import GoogleTranslator
from typing import Any
from pathlib import Path
from tqdm import tqdm
from collections import OrderedDict

def translate_text(text: str, target_lang: str) -> str:
    """
    Uses GoogleTranslator to translate the text.
    """
    translator = GoogleTranslator(source='auto', target=target_lang)
    return translator.translate(text)

def preserve_placeholders(text: str, target_lang: str) -> str:
    """
    Protects substrings enclosed in {} from being translated.
    This function splits the text into translatable parts and non-translatable placeholders,
    translates only the translatable parts, and then reassembles everything.
    """
    # Regular expression to match placeholders like {someone}
    pattern = r'(\{[^}]+\})'
    
    # Split the text by placeholders
    parts = re.split(pattern, text)
    
    # If no placeholders, just translate the whole text
    if len(parts) == 1:
        return translate_text(text, target_lang)
    
    # Translate only the non-placeholder parts
    for i in range(0, len(parts), 2):  # Even indexes are non-placeholder text
        if parts[i].strip():  # Only translate non-empty strings
            parts[i] = translate_text(parts[i], target_lang)
    
    # Reassemble the text with untranslated placeholders
    return ''.join(parts)

def process_dict(d: dict, target_lang: str, pbar: tqdm) -> dict:
    """
    Recursively processes a dictionary, translating all string values.
    """
    for key, value in d.items():
        if isinstance(value, str):
            # Update progress bar for each string processed
            pbar.update(1)
            d[key] = preserve_placeholders(value, target_lang)
        elif isinstance(value, dict):
            process_dict(value, target_lang, pbar)
    return d

def count_strings(d: dict) -> int:
    """
    Recursively counts the number of string values in the dictionary.
    """
    count = 0
    for value in d.values():
        if isinstance(value, str):
            count += 1
        elif isinstance(value, dict):
            count += count_strings(value)
    return count

def parse_js_object(js_content: str) -> Any:
    """
    Converts a JS file content (with export default) into a Python dict.
    Assumes the input file follows a format similar to the provided example.
    """
    try:
        # Remove "export default" and any trailing semicolon
        js_content = js_content.strip()
        if js_content.startswith("export default"):
            js_content = js_content[len("export default"):].strip()
        if js_content.endswith(";"):
            js_content = js_content[:-1]

        # Convert unquoted keys to quoted keys for valid JSON
        js_content = re.sub(r'(?<!["\"])\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s*:)', r'"\1"', js_content)

        # Handle numeric keys by quoting them
        js_content = re.sub(r'(?<=\{|,|\s)(\d+)(?=\s*:)', r'"\1"', js_content)

        # Handle single quotes in values by replacing them with double quotes
        js_content = re.sub(r':\s*\'(.*?)\'', r': "\1"', js_content)

        # Ensure no trailing commas in objects or arrays
        js_content = re.sub(r',\s*([}\]])', r'\1', js_content)

        # Parse the JSON content
        return json.loads(js_content, object_pairs_hook=OrderedDict)
    except json.JSONDecodeError as e:
        # Provide detailed error information
        raise ValueError(f"Error parsing JS object: {e.msg} at line {e.lineno} column {e.colno} (char {e.pos})")

def write_js_object(data: dict) -> str:
    """
    Converts a Python dict back into a JS object string without wrapping keys in double quotes
    unless necessary (e.g., if the key contains special characters or spaces).
    Ensures that non-ASCII characters are not escaped and formats the output with newlines.
    """
    def dict_to_js(obj, indent=0):
        if isinstance(obj, dict):
            items = []
            for key, value in obj.items():
                # Only wrap keys in quotes if they are not valid JS identifiers
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                    key_str = key
                else:
                    key_str = json.dumps(key, ensure_ascii=False)
                value_str = dict_to_js(value, indent + 2)
                items.append(f"{' ' * (indent + 2)}{key_str}: {value_str}")
            return "{\n" + ",\n".join(items) + f"\n{' ' * indent}}}"
        elif isinstance(obj, str):
            return json.dumps(obj, ensure_ascii=False)
        else:
            return json.dumps(obj, ensure_ascii=False)

    return "export default " + dict_to_js(data) + ";\n"

def main():
    if len(sys.argv) < 2:
        print("Usage: python translate.py <target_language>")
        sys.exit(1)
    target_lang = sys.argv[1]
    
    # Read the input.js file using pathlib
    input_path = Path("input.js")
    if not input_path.exists():
        print("Error: input.js not found!")
        sys.exit(1)
    js_content = input_path.read_text(encoding="utf-8")
    
    try:
        data = parse_js_object(js_content)
    except Exception as e:
        print("Error parsing input.js:", e)
        sys.exit(1)
    
    # Count total strings for progress tracking
    total = count_strings(data)
    print(f"Found {total} string(s) to translate.")
    
    # Process the translations using tqdm to show progress
    with tqdm(total=total, desc="Translating") as pbar:
        translated_data = process_dict(data, target_lang, pbar)
    
    # Write the translated output preserving the export default syntax
    output_content = write_js_object(translated_data)
    output_path = Path("output.js")
    output_path.write_text(output_content, encoding="utf-8")
    
    print("Translation completed. Output written to output.js")

if __name__ == "__main__":
    main()
