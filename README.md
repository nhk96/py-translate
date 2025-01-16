# py-translate

A Python script designed to translate JavaScript files using Google Translator while preserving nested structures and placeholders.

## Features

- Translates JavaScript files from English to a target language.
- Maintains nested structures and placeholders.
- Supports batch translation to minimize API calls.
- Tracks progress for both translation and file generation.

## Dependencies

- `deep_translator`
- `tqdm`

Install the required dependencies using pip:

```sh
pip install deep-translator tqdm
```

## Usage

1. Place your input JavaScript file in the project directory.
2. Update the `input_file`, `output_file`, and `target_language` variables in the script as needed.
3. Execute the script:

```sh
python translate.py
```

## Example

```sh
python translate.py
```

This command will translate the `input.txt` file to Simplified Chinese and save the result as `output.txt`.

## Supported String Formats

The following string formats are supported for translation:
```javascript
{
    key1: "value",
    key2: 'value',
    key3: `value`,
    "key4": "value",
    'key5': "value",
    `key6`: "value`,
    key7: `this is "value" string`,

    nestedKey: {
        key1: "value",
        key2: 'value',
        key3: `value`,
        "key4": "value",
        'key5': "value",
        `key6`: "value",
        key7: `this is "value" string`
    }
}
```

**Note:** The current implementation will replace the translated value with `""` and will not preserve the original quotes if the value is wrapped in `''` or ````.

### Example Input and Output

Given the input:

```javascript
{
    test1: "test",
    test2: 'test',
    test3: `test`,
    "test4": "test",
    'test5': "test",
    `test6`: "test`,
    test7: `this is "test" string`,

    testNested: {
        test1: "test",
        test2: 'test',
        test3: `test`,
        "test4": "test",
        'test5': "test",
        `test6`: "test",
        test7: `this is "test" string`
    }
}
```

The output will be:

```javascript
{
    test1: "测试",
    test2: "测试",
    test3: "测试",
    "test4": "测试",
    'test5': "测试",
    `test6`: "测试`,
    test7: "这是",
    testNested: {
        test1: "测试",
        test2: "测试",
        test3: "测试",
        "test4": "测试",
        'test5': "测试",
        `test6`: "测试`,
        test7: "这是"
    }
}
```

**Note:** The current code cannot handle nested strings inside double quotes and will convert all values with `''` and `` quotes to `""`.

## File Statistics

The script also prints statistics about the input file, such as the total number of lines and characters.

## License

This project is licensed under the MIT License.