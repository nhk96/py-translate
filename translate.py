import os
import re
from deep_translator import GoogleTranslator
import time
from typing import List, Tuple, Any
from pathlib import Path
from tqdm import tqdm
from collections import OrderedDict

# Update regex patterns to catch all possible string formats
KEY_VALUE_PATTERN = re.compile(r'(["\'`]?)(\w+)\1:\s*["\'`]?([^"\'`]+)["\'`]?')
NESTED_OBJECT_PATTERN = re.compile(r'(["\'`]?)(\w+)\1:\s*\{([^{}]+(?:\{[^{}]+\}[^{}]*)*)\}')
PLACEHOLDER_PATTERN = re.compile(r'\{[^}]+\}')

def batch_translate(texts: List[str], translator: GoogleTranslator, batch_size: int = 10) -> List[str]:
    """Translate texts in batches to reduce API calls."""
    translations = []
    total_batches = (len(texts) + batch_size - 1) // batch_size
    
    with tqdm(total=len(texts), desc="Translating", unit="text") as pbar:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                translated_batch = translator.translate_batch(batch)
                translations.extend(translated_batch)
                pbar.update(len(batch))
            except Exception as e:
                print(f"\nBatch translation error, falling back to individual translation: {e}")
                for text in batch:
                    try:
                        translation = translator.translate(text)
                        translations.append(translation)
                        pbar.update(1)
                    except Exception as e:
                        print(f"\nTranslation error: {e}")
                        translations.append(text)
                        pbar.update(1)
    return translations

def process_text(text: str) -> Tuple[str, List[str]]:
    """Process text by extracting and replacing placeholders."""
    placeholders = []
    
    def store_placeholder(match):
        placeholder = match.group(0)
        placeholders.append(placeholder)
        return f'PLACEHOLDER_{len(placeholders)-1}'
    
    processed_text = PLACEHOLDER_PATTERN.sub(store_placeholder, text)
    return processed_text, placeholders

def extract_nested_content(content: str) -> OrderedDict:
    """Extract content from nested structure maintaining original order with improved capturing."""
    result = OrderedDict()
    items = []
    
    # Process nested objects first
    for match in NESTED_OBJECT_PATTERN.finditer(content):
        quote, key, nested_content = match.groups()
        # Only create nested object if there's actual content
        if nested_content.strip():
            nested_pairs = OrderedDict()
            # Process nested key-value pairs with all possible string formats
            for nested_match in KEY_VALUE_PATTERN.finditer(nested_content):
                nested_quote, nested_key, nested_value = nested_match.groups()
                nested_pairs[(nested_key.strip(), nested_quote)] = nested_value.strip()
            
            # Only add nested object if it has content
            if nested_pairs:
                items.append((match.start(), (key, quote), nested_pairs))

    # Process regular key-value pairs
    for match in KEY_VALUE_PATTERN.finditer(content):
        quote, key, value = match.groups()
        # Don't add if it's already handled as a nested object
        if not any(key == item[1][0] for item in items):
            items.append((match.start(), (key, quote), value))

    # Sort by position and create ordered result
    for _, (key, quote), value in sorted(items, key=lambda x: x[0]):
        # Only create nested object if value is dict and has content
        if isinstance(value, dict) and value:
            result[(key, quote)] = value
        elif not isinstance(value, dict):
            result[(key, quote)] = value

    return result

def translate_nested_content(content: OrderedDict, translator: GoogleTranslator) -> OrderedDict:
    """Translate content while preserving nested structure and order."""
    translated = OrderedDict()
    texts_to_translate = []
    translation_map = OrderedDict()
    sequence_map = []  # Store sequence of keys
    
    # First pass: collect all texts and show progress
    total_items = sum(1 if not isinstance(v, dict) else len(v) for v in content.values())
    print(f"\nCollecting {total_items} items for translation...")
    
    def collect_texts(item: OrderedDict):
        collected_count = 0
        for (k, quote), v in item.items():
            if isinstance(v, dict):
                sequence_map.append(('dict_start', (k, quote)))
                sub_count = collect_texts(v)
                collected_count += sub_count
                sequence_map.append(('dict_end', (k, quote)))
            else:
                processed_text, placeholders = process_text(v)
                texts_to_translate.append(processed_text)
                translation_map[(k, quote)] = placeholders
                sequence_map.append(('text', (k, quote)))
                collected_count += 1
        return collected_count

    collected_count = collect_texts(content)
    print(f"Collected {collected_count} items for translation")
    
    # Translate all collected texts with progress bar
    translated_texts = batch_translate(texts_to_translate, translator)
    translated_dict = dict(zip(translation_map.keys(), translated_texts))

    # Rebuild the structure following original sequence
    current_dict = translated
    dict_stack = []
    text_index = 0

    for action, (key, quote) in sequence_map:
        if action == 'dict_start':
            translated[(key, quote)] = OrderedDict()
            dict_stack.append(current_dict)
            current_dict = translated[(key, quote)]
        elif action == 'dict_end':
            current_dict = dict_stack.pop()
        else:  # action == 'text'
            translated_text = translated_texts[text_index]
            placeholders = translation_map[(key, quote)]
            for i, placeholder in enumerate(placeholders):
                translated_text = translated_text.replace(f'PLACEHOLDER_{i}', placeholder)
            current_dict[(key, quote)] = translated_text
            text_index += 1

    return translated

def generate_js_content(translated_content: OrderedDict, indent: int = 2, wrap_with_braces: bool = True, include_export_default: bool = False) -> str:
    """Generate JS content with proper formatting and sequence."""
    lines = ['export default {'] if include_export_default else (['{'] if wrap_with_braces else [])
    
    def format_value(v: Any) -> str:
        if isinstance(v, dict):
            nested_lines = ['{']
            for (nk, nq), nv in v.items():
                nested_lines.append(f'{" " * (indent * 2)}{nq}{nk}{nq}: "{nv}",')
            nested_lines.append(f'{" " * indent}}}')
            return '\n'.join(nested_lines)
        return f'"{v}"'

    for (key, quote), value in translated_content.items():
        formatted_value = format_value(value)
        if isinstance(value, dict):
            lines.append(f'{" " * indent}{quote}{key}{quote}: {formatted_value},')
        else:
            lines.append(f'{" " * indent}{quote}{key}{quote}: {formatted_value},')
    
    if wrap_with_braces or include_export_default:
        lines.append('}')
    return '\n'.join(lines)

def translate_js_file(input_file: str, output_file: str, target_language: str) -> None:
    """Optimized translation function with progress tracking."""
    if not Path(input_file).exists():
        print(f"Error: Input file '{input_file}' does not exist.")
        return

    translator = GoogleTranslator(source='en', target=target_language)
    
    try:
        print(f"\nReading file: {input_file}")
        content = Path(input_file).read_text(encoding='utf-8')
        parsed_content = extract_nested_content(content)
        
        if not parsed_content:
            print("No translatable content found.")
            return

        start_time = time.time()
        
        # Translate content with progress tracking
        translated_content = translate_nested_content(parsed_content, translator)
        
        print("\nGenerating output file...")
        wrap_with_braces = content.strip().startswith('{') and content.strip().endswith('}')
        include_export_default = 'export default' in content
        final_content = generate_js_content(translated_content, wrap_with_braces=wrap_with_braces, include_export_default=include_export_default)
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(final_content, encoding='utf-8')
        
        total_time = time.time() - start_time
        print(f"\nTranslation completed successfully!")
        print(f"Output file: '{output_file}'")
        print(f"Total time: {total_time:.2f}s")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        return


if __name__ == "__main__":
    input_file = "input.txt"
    output_file = "output.txt"
    target_language = "zh-CN"
    
    # Add file statistics
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"\nInput file statistics:")
        print(f"Total lines: {len(content.splitlines())}")
        print(f"Total characters: {len(content)}")
    
    translate_js_file(input_file, output_file, target_language)